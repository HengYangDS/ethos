# Design: pre-adoption legacy refs and the legacy-role closeout

## Context

See `proposal.md` — Why. The repositories in this shape are adopted under a legacy branch-role
table and hold refs at commits made before the adoption, which carry no repository profile. Five
repairs (a1, c2, a2, c1, b2) are built; a sixth (b1) is not in this Change. The "Today" lines
below were read at the base `024c217bf` on 2026-11-21; the tests are
`tests/unit/lanes/test_pre_adoption_legacy_refs.py`.

## Goals / Non-Goals

**Goals.** An abandonment blocks before any effect when the hook would refuse its ref deletion.
A closeout renames a legacy release ref that stands before the table's commit, and the release
mirror and the release advance from such a commit. A legacy ref with no shared history is refused
by its own name. The protection reads the accepted head's table as well as the deleted commit's.

**Non-Goals.** The forge retirement of published legacy refs stays as it is (the owner,
2026-11-20: deleted by hand). No new command, flag or profile key. A hand deletion of a legacy ref
stays refused. The rename of a legacy ref at a retired-schema profile (b1) is not in this Change:
it changes a sentence of the identity requirement and waits for the owner's answer.

## Decisions

Five repairs at five sites. Line numbers in the call chains are those of the base `024c217bf`.

### a1 — the deletion policy at an accepted head with no release binding

- Call chain: `hook/admission.py:370` `_prepared_reference_report` → `:388`
  `resolve_ref_move_policy` → `adapters/admission/ref_move_policy.py:198-224` (strict old,
  strict new, inline profile fallback `:214-219`, then `_absorbed_ref_transition_policy`
  `:236-266`).
- Today: the fallback returns `None` when the accepted head's committed release binding is not a
  strict policy (`:246`), HEAD is not the accepted branch (`:249`), the branch is not a topic
  (`:250`), or a compensating contribution fails (`:251-254`); `resolve_ref_move_policy` turns
  `None` into `ref_move_policy_unavailable` (`:222-224`).
- Built: in `_absorbed_ref_transition_policy`, when `_strict_ref_policy(repo, accepted_head)` is
  `None` and `load_committed_repository_profile(repo, accepted_head)` is valid with a
  declaration, the policy is `BranchRolePolicy()`. With neither the deletion stays refused.
  Signatures unchanged.
- Reuse: `load_committed_repository_profile` (`profile.py:25-52`, already used at `:216`),
  `BranchRolePolicy()` (`contracts/branch/roles.py:78-85`), `load_branch_role_policy`
  (`roles.py:231-236`), `git_stdout`, `accepted_contribution`/`report_verdict`.

### c2 — the legacy protection reads the accepted head's table too

- Call chain: `role_rename.py:145-161` `legacy_role_ref_protected` → `:155` `legacy_role_renames`
  (`:53-61`) → `committed_file_text(root, old_value, binding_path("workspace"))`. Called from
  `ref_move_policy.py:277` (`prepared_deletion_gaps`) and `role_rename.py:140`
  (`role_rename_ref_report`, after `plan_ref_intents` at `:125-139`). `prepared_deletion_gaps`'
  only live caller is `mutation/lane_retirement/absorbed.py:108`.
- Today: for `refs/heads/master` at a table-less pre-adoption commit, the read yields `''`,
  `legacy_role_renames` yields `{}`, the ref is not protected, and `prepared_deletion_gaps`
  returns `[]`; the accepted table, which declares `master`, is never read.
- Built: `legacy_role_ref_protected` and the hook's shape check `_rename_shape_gaps` union the
  deleted commit's table with the accepted one, read at `_accepted_table_head(repo)`: the head
  of the accepted ref, so that every root of the repository gets one answer whatever it has
  checked out. The successor exemption applies to the union. Signatures are unchanged
  (`legacy_role_ref_protected(repo, ref_name, old_value, new_value)`,
  `prepared_deletion_gaps(repo, ref_name, old_value)`).

### a2 — the abandonment asks the hook's deletion predicate first

- Call chain: `lane retire abandon` → `application/lane/retirement.py:58` →
  `derive_lane_abandonment` (`abandonment.py:93`); validation and coordinates `:104-147`; receipt
  compile and persist `:148-160`. Apply re-runs the receipt's action through
  `operation.py:551/:571` → preflight `:504/:335` → `:519-520` iterates `remaining_effects`
  (`remove_worktree` before `delete_ref`), each admitted at `:370-371`.
- Today: nothing between derivation and removal consults the hook; on apply the worktree is
  removed before the ref deletion is admitted, so a refusal leaves `lane_retirement_partial`.
- Built: the derivation asks `prepared_deletion_gaps` before it compiles or persists
  (`abandonment.py` `_refuse_unadmitted_deletion`); a refusal yields verdict `block`, state
  `blocked`, the hook's gaps and no `next_action`, and no receipt is persisted. The symbol is
  imported at module scope in `abandonment.py`, which the module's test replaces.
- Built: the apply preflight asks the same predicate before anything is removed, so a receipt
  derived while the ref was unprotected cannot take the worktree down for a deletion that now
  refuses. The two admissions an apply asks (deletion, reviewed content) live in
  `lane_retirement/effects.py`, the retirement effects' owner, beside the other effect
  admissions.

### c1 — a pre-adoption pre-state is read under the accepted head's identity

- Call chain: `git_effect_admission.py:42` `admit_git_effect_state` → `:71-78`
  `resolve_git_effect_repository` (`git_effect_observation.py:71`) → `:115-121`
  `repository_identities` (`profile.py:70`) → `historical_repository_identity` (`profile.py:133`,
  raising `repository_historical_identity_invalid:<path>`), then the identity agreement check
  `:129-131`. Second entry: `git_effect_attestation.py:187-199`. Closeout caller:
  `branch_roles.py:335` → `:405`/`:411`.
- Today: a pre-state revision without a profile is refused by blob absence. Moving such revisions
  out of `historical` instead is wrong: they would be read under today's schema and raise
  `repository_profile_invalid`.
- Built: `_effect_identities` reads every revision as before; only when a historical read
  fails does it ask which expected pre-states belong to the adopted line without a profile
  (`_pre_adoption_prestates`), and reads the rest again without them. An effect whose
  identities all resolve spends no extra read, which the read-budget tests of
  `test_historical_profile_identity.py` hold. With no such pre-state the first refusal is raised
  unchanged. `_validate_historical_source` (`commit/signature.py`) is NOT a c1 site and is not
  touched.

### b1 — the rename's shared OID is not a produced revision (not in this Change)

- Call chain: `operation.py:97` `_legacy_role_result` → `branch_roles.py:349` → `:393-403`
  updates `{legacy: head→0, target: 0→head}` → `compile_observed_git_effect` → the same
  resolver.
- Today: `git_effect_observation.py:110-114` classifies `produced = revisions & {update.desired}`;
  a rename's OID is both expected and desired, so the legacy commit is read under today's reader.
- Not built. The rule would classify as produced only OIDs created by this effect (desired
  non-zero whose expected is zero), not any OID also deleted by it; it changes the identity
  requirement's sentence on produced revisions, so it waits for the owner's answer and takes a
  Change of its own. Until then a legacy ref at a retired-schema profile stays refused.

### b2 — the unshared legacy ref is refused by name

- Call chain: `rename_legacy_roles` (`branch_roles.py:335`): table at `current_head` `:348-354`,
  declared-accepted check `:357`, gaps `:359-391`, compile `:393-403`; preview `:405`, apply
  `:411` → the shape check in `role_rename.py:120-142` (`:164-201`).
- Built: one classification, `adoption_classification(root, revision, *, accepted_head)` in
  `adapters/repo/profile.py`, answers `adopted` (no commit of the revision's history carries
  the profile path, and the accepted head descends from it), `dropped` (its history once
  carried the profile) or `unshared`. c1 asks it through `predates_adoption`; the rename asks it
  once for each legacy head whose identity cannot be read. `unshared` is refused with
  `legacy_role_rename_history_unshared:<branch>`, `dropped` keeps
  `repository_historical_identity_invalid:<profile path>`, and the refusals come before both the
  preview and the apply. The rename's plan carries no pre-state flag: its admission comes from
  c1's reading of the legacy commit. The gap code is registered in `contracts/codes/gaps.toml`
  (owner `adapters.mutation`, the branch after the colon).

### Order and conflicts

1. a1 and c2 land in ONE commit. Without c2, a1's default policy makes the deletion of `master`
   admissible before its rename (`master` is `ROLE_OTHER` under the `work/` prefix, so a topic).
2. b1 and c1 sit in one function on the closeout path. c1 alone renames a legacy ref at a commit
   with no profile, which the cases show; a legacy ref at a retired-schema profile needs b1.
3. After a1, the reported `submit/` ref is not a legacy role ref and `prepared_deletion_gaps`
   returns `[]` for it; a2 closes the class, not that case alone.
4. c2 reads the accepted ref's head. Before the accepted role itself is renamed that ref does not
   exist, and the asking root's HEAD stands in; the closeout runs from the accepted root, whose
   HEAD carries the table. A root checked out before the table, in a repository whose accepted
   name is legacy too, does not see it: a deletion asked there is judged by the deleted commit's
   own table alone.
5. The profile's history is read at its current path. A repository that moved its profile path
   would read as having carried none; no governed repository has moved it, and the paradigm
   fixes the path.
6. a1's default policy uses the paradigm's names, not the names of the accepted head's committed
   table. A repository whose table names another topic prefix keeps its own topic refused there
   (fail closed); every admitted deletion still needs a claimed `lane.retire` intent.

## Risks / Trade-offs

### Measured evidence

- The module as first drafted held 14 cases: 12 failed on `024c217bf` and the two forge
  retirement cases passed, holding today's refusal. Every case of the module passes at the lane
  head. The half-done state is built by a lock file on the ref so the deletion stops after the
  worktree removal; the same step re-run ends it.
- Without b1 (`probe-two-repairs-k1-b2c1.out`, 2026-11-20 16:53): `master` renames; the
  retired-schema case is the one that needs b1.

## Migration Plan

No migration: every change admits what is refused today or adds a refusal the accepted scenario
already states. A repository without a legacy table reads as before. Rollback is the revert of
this Change's commits before its landing.

## Open Questions

- b1 and its sentence of the identity requirement wait for the owner's answer (asked 2026-11-21);
  they are not in this Change. Until then the rename from a retired-schema profile stays refused.
