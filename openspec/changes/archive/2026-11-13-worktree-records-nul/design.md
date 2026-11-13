# Design

## Context

See the [proposal](proposal.md) and the [delta](specs/adapters/spec.md). Git documents the porcelain
format in git-worktree(1) (Git 2.56.1 here), under "Porcelain Format" and the `-z` option: each
attribute is a line, `-z` ends every line with NUL instead of a newline, an empty line ends a
record, and the first attribute of a record is always `worktree`. A label and its value are
separated by one space. `bare` and `detached` are labels alone; `locked` is a label alone or a
label and its reason, depending on whether a reason exists; the documented example shows
`prunable` with its reason. Without `-z`, Git quotes a lock reason that holds a newline or other
unusual characters as `core.quotePath` describes; with `-z` it writes the reason as recorded. The
`-z` option names the path case itself: it makes a listing parseable when a worktree path holds a
newline.

At cfc6bc479 these sites read the listing, the product ones under `src/ethos/adapters/`:

- The newline form: `repo/worktree_effects.py` (`raw_worktree_records`),
  `admission/role_rename.py`, `repo/attestation_lifetime_facts.py`, `repo/runtime/authority.py`,
  `mutation/branch_roles.py`, `mutation/lane_lifecycle/start.py`,
  `mutation/lane_lifecycle/handoff/destination_cleanup.py`, `mutation/worktree/detached_cleanup.py`,
  `repo/commit/rebuild/readiness.py` and `repo/status/workspace.py`.
- The `-z` form, each split by hand: `repo/hook/activation.py`, `repo/runtime/retirement.py`,
  `store/retention/writers.py`, `mutation/accepted/release.py` and
  `tools/ci/delivery/acceptance/brownfield.py`.
- Consumers of `raw_worktree_records`: `worktree_effects.worktree_record`,
  `mutation/lane_retirement/operation.py` and `repo/commit/signature.py`.

`ethos lane status --json` emits `workspace_status` as its `data`, whose `worktrees` come from
`repo/status/workspace.py`.

## Goals / Non-Goals

**Goals:**

- One parser and one invocation of `git worktree list --porcelain -z` for the product and its
  delivery tools, so a path or a lock reason that holds a newline is one value everywhere.
- Each site keeps what a failed listing meant to it.
- Lane status reports each record whole, with lock and prune states and their reasons.

**Non-Goals:**

- Other `--porcelain` readers, such as `git status` and `git push`.
- Test helpers that only check that a path appears in a listing.
- A new command, or a new result schema version.
- Making the lenient sites fail closed; each keeps its current fallback.

## Decisions

1. `src/ethos/adapters/repo/worktree_list.py` owns the observation. Every reader already imports
   `ethos.adapters.repo.git`, and the new module imports only that module and
   `ethos.contracts.outcome`, so no reader gains a dependency or an import cycle. The
   `ethos-internal-layers` contract holds, since every reader sits in `ethos.adapters` or in
   `tools`. `git.py` was the first candidate, but it has 490 of its 500 effective lines and the
   new module needs 34. `worktree_effects.py` owns worktree effects, not their observation;
   importing it would give `hook/activation.py`, `runtime/retirement.py`, `runtime/authority.py`
   and `attestation_lifetime_facts.py` a runtime import closure of 32 modules, where the new
   module brings 8 that they already load.
2. `parse_worktree_list(listing)` splits records at the empty attribute (`\0\0`) and attributes at
   NUL, and maps each label to the text after its first space. A label alone maps to the empty
   string, so a caller tests a flag with `in`, as the callers of `raw_worktree_records` already do.
   An empty field never becomes a label, so a listing without its final terminator still yields
   its last record.
3. `listed_worktrees(root, environment=, runner=)` runs the command and returns None when Git exits
   non-zero; `raw_worktree_records(root, environment=, runner=, gap=)` refuses with `gap` instead.
   A Git that cannot start or exceeds its deadline still raises from `run_git`, as at every site
   before.
4. Each site keeps what a failed listing meant to it:
   - `role_rename` (`retained_topic_worktree_binding_mismatch`), `handoff/destination_cleanup`
     (`handoff_import_compensation_failed`), `hook/activation` and `runtime/retirement`
     (`hook_runtime_worktrees_unreadable`) and `retention/writers`
     (`record_retirement_worktrees_unreadable`) pass the code they raised as `gap`.
   - `runtime/authority`, `branch_roles` and `lane_lifecycle/start` read a failed listing as no
     worktree, so they read `listed_worktrees(...) or ()`: the repository root, no rebinding and
     `lane_start_target_path_exists` follow as before. `start` now compares the `worktree`, `HEAD`
     and `branch` values for equality instead of finding a substring of the listing.
   - `worktree/detached_cleanup` maps None to its inventory failure, as before.
   - `attestation_lifetime_facts` raised `CalledProcessError`, which `attestation_set` reports as
     a lifetime gap; it now passes `REFS_UNAVAILABLE`, which `attestation_set` reports the same way.
   - `status/workspace`, `accepted/release` and `commit/rebuild/readiness` raised
     `CalledProcessError`; they now raise the default refusal.
   - `brownfield` keeps the raw listing that it compares before and after, and parses that same
     text with `parse_worktree_list`.
   - `branch_roles._worktrees` is gone; its two callers read the owner directly.
   - Where a test replaces a module's `run_git` (`lane_retirement/operation`,
     `worktree/detached_cleanup`, `runtime/retirement`) or a caller injects one
     (`handoff/destination_cleanup`), the site passes that name as `runner`, so the seam holds.
5. Lane status names the new fields `prunable` (`"true"` or `"false"`) and `prune_reason` (Git's
   reason or `""`), in the shape of `locked` and `lock_reason`. The workspace-status schema
   declares and requires both.
6. `Work Lane Topology` is the one requirement that governs reported worktree metadata, so it is
   modified: it restates its two scenarios and adds one.

## Risks / Trade-offs

- Where a failed listing raised `CalledProcessError` (status, release, rebuild readiness), it now
  raises the refusal `worktree_effect_observation_failed`. Release blocked on either, rebuild
  readiness now reports a blocked result where the error escaped, and status raises to its
  caller as before. `hook/activation` reports its code instead of Git's stderr, and the lifetime
  gap names `attestation_lifetime_refs_unavailable` instead of the `CalledProcessError` text.
  Each failure still fails; its text changes.
- The lifetime facts read the listing in the ordinary Git environment instead of the observation
  environment. Both set `GIT_CONFIG_GLOBAL` to the null device and `GIT_CONFIG_NOSYSTEM`, and the
  listing reads no other configuration, so the records are the same.
- A consumer that parsed a quoted `lock_reason` now receives the reason as written.
- Git translates the prune reason; `run_git` sets `LC_ALL=C`, so status reports it in English.
