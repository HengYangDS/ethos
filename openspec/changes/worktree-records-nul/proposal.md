# Proposal

## Why

ETHOS reads `git worktree list --porcelain` in fourteen product modules and one delivery acceptance
tool, each through its own parser. Ten of them split the newline-terminated form, so a worktree
whose path holds a newline, which Git allows on macOS and Linux, is misread: its path ends at the
newline and the rest becomes a stray attribute or a false record, lookups by path miss it, and
`ethos lane status --json` reports a wrong path. That form also quotes a lock reason that holds a
newline or other unusual characters. Git documents `-z` for exactly this case (git-worktree(1), the
`-z` option and "Porcelain Format"). The four modules and the tool that already pass `-z` each split
it by hand and keep only some attributes. An adopter, di-effect, was promised this Change by name.

## What Changes

- One owner reads the listing: `src/ethos/adapters/repo/worktree_list.py` runs
  `git worktree list --porcelain -z` and maps each NUL-terminated record to its labels and exact
  values. `raw_worktree_records` moves there from `worktree_effects.py` and refuses with the
  caller's gap, `worktree_effect_observation_failed` unless the caller names its own.
- Every reader of the listing uses that owner and keeps its own refusal code or fallback; the
  design lists each site.
- Each `data.worktrees` entry of `ethos lane status --json` comes from that owner and gains
  `prunable` and `prune_reason` beside `locked` and `lock_reason`. `lock_reason` is the reason as
  Git records it, no longer quoted. `system/schemas/kernel/workspace-status.schema.json` declares
  the two fields. The change is additive; no command, flag or result schema version changes.
- The Unreleased section of `CHANGELOG.md` gains a Fixed line and an Added line for the two new
  `lane status` fields.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: `Work Lane Topology` reports each worktree from one whole Git record and gains a
  scenario for paths and lock reasons that hold a newline and for locked and prunable worktrees.

## Impact

`src/ethos/adapters/repo/worktree_list.py` (new), `worktree_effects.py`,
`attestation_lifetime_facts.py`, `commit/signature.py`, `commit/rebuild/readiness.py`,
`hook/activation.py`, `runtime/authority.py`, `runtime/retirement.py` and `status/workspace.py`
under `src/ethos/adapters/repo/`; `admission/role_rename.py`, `mutation/branch_roles.py`,
`mutation/accepted/release.py`, `mutation/lane_lifecycle/start.py`,
`mutation/lane_lifecycle/handoff/destination_cleanup.py`, `mutation/lane_retirement/operation.py`,
`mutation/worktree/detached_cleanup.py` and `store/retention/writers.py` under
`src/ethos/adapters/`; `tools/ci/delivery/acceptance/brownfield.py`;
`system/schemas/kernel/workspace-status.schema.json`; `CHANGELOG.md`; the new
`tests/unit/adapters/repo/test_worktree_list.py` and three tests whose fake listings now use the
NUL form. Out of scope: other `--porcelain` readers such as `git status` and `git push`, and the
test helpers that only check that a path appears in a listing.
