# Design: pre-adoption legacy refs and the legacy-role closeout

## Context

See `proposal.md` — Why. The repositories in this shape are adopted under a legacy branch-role
table and hold refs at commits made before the adoption, which carry no repository profile. Six
repairs (a1, c2, a2, c1, b1, b2) touch five sites. Every claim below was read at the lane head
`024c217bf` on 2026-11-21; the failing tests are
`tests/unit/lanes/test_pre_adoption_legacy_refs.py`.

## Goals / Non-Goals

**Goals.** An abandonment blocks before any effect when the hook would refuse its ref deletion.
A closeout renames a legacy release ref that stands before the table's commit, and the release
mirror and the release advance from such a commit. A legacy ref with no shared history is refused
by its own name. The protection reads the accepted root's table as well as the deleted commit's.

**Non-Goals.** The forge retirement of published legacy refs stays as it is (the owner,
2026-11-20: deleted by hand). No new command, flag or profile key. A hand deletion of a legacy ref
stays refused. The rename's second part (b1) waits for the owner's answer on the identity
requirement's sentence; without it the retired-schema case stays out of the module.

## Decisions

Read at the lane head `024c217bf` on 2026-11-21. Six repairs (a1, c2, a2, c1, b1, b2) at five
sites. b1 waits for the owner's answer on the identity requirement's second sentence; without it
the retired-schema case stays out of the module.

### a1 — the deletion policy at an accepted head with no release binding

- Call chain: `hook/admission.py:370` `_prepared_reference_report` → `:388`
  `resolve_ref_move_policy` → `adapters/admission/ref_move_policy.py:198-224` (strict old,
  strict new, inline profile fallback `:214-219`, then `_absorbed_ref_transition_policy`
  `:236-266`).
- Today: the fallback returns `None` when the accepted head's committed release binding is not a
  strict policy (`:246`), HEAD is not the accepted branch (`:249`), the branch is not a topic
  (`:250`), or a compensating contribution fails (`:251-254`); `resolve_ref_move_policy` turns
  `None` into `ref_move_policy_unavailable` (`:222-224`).
- Change: `ref_move_policy.py:246-256`. When `_strict_ref_policy(repo, accepted_head)` is `None`
  and `load_committed_repository_profile(repo, accepted_head)` is valid with a declaration, use
  `BranchRolePolicy()`. Fail closed with neither. Signatures unchanged.
- Reuse: `load_committed_repository_profile` (`profile.py:25-52`, already used at `:216`),
  `BranchRolePolicy()` (`contracts/branch/roles.py:78-85`), `load_branch_role_policy`
  (`roles.py:231-236`), `git_stdout`, `accepted_contribution`/`report_verdict`.

### c2 — the legacy protection reads the accepted root's table too

- Call chain: `role_rename.py:145-161` `legacy_role_ref_protected` → `:155` `legacy_role_renames`
  (`:53-61`) → `committed_file_text(root, old_value, binding_path("workspace"))`. Called from
  `ref_move_policy.py:277` (`prepared_deletion_gaps`) and `role_rename.py:140`
  (`role_rename_ref_report`, after `plan_ref_intents` at `:125-139`). `prepared_deletion_gaps`'
  only live caller is `mutation/lane_retirement/absorbed.py:108`.
- Today: for `refs/heads/master` at a table-less pre-adoption commit, the read yields `''`,
  `legacy_role_renames` yields `{}`, the ref is not protected, and `prepared_deletion_gaps`
  returns `[]`; the HEAD table, which declares `master`, is never read.
- Change: `role_rename.py:155-161`. Union `legacy_role_renames(repo, old_value)` with
  `legacy_role_renames(repo, git_stdout(repo, "rev-parse", "HEAD"))` (empty when unreadable); keep
  the `:160-161` successor exemption against the union. Signatures are fixed by positional callers:
  `legacy_role_ref_protected(repo, ref_name, old_value, new_value)` and
  `prepared_deletion_gaps(repo, ref_name, old_value)`.

### a2 — the abandonment asks the hook's deletion predicate first

- Call chain: `lane retire abandon` → `application/lane/retirement.py:58` →
  `derive_lane_abandonment` (`abandonment.py:93`); validation and coordinates `:104-147`; receipt
  compile and persist `:148-160`. Apply re-runs the receipt's action through
  `operation.py:551/:571` → preflight `:504/:335` → `:519-520` iterates `remaining_effects`
  (`remove_worktree` before `delete_ref`), each admitted at `:370-371`.
- Today: nothing between derivation and removal consults the hook; on apply the worktree is
  removed before the ref deletion is admitted, so a refusal leaves `lane_retirement_partial`.
- Change: after `:147`, before compile, call
  `prepared_deletion_gaps(control_root, f"refs/heads/{branch}", head)` and refuse with its gaps;
  `_blocked` (`:39-48`) yields verdict `block`, state `blocked`, the gaps, and no `next_action`,
  and no receipt is persisted. Import the symbol at module scope in `abandonment.py` (the test
  monkeypatches `abandonment.prepared_deletion_gaps`). Also check in `preflight_operation` before
  `:370` so a stored receipt cannot remove the worktree first; that half is reasoned, not yet
  test-proven.

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
- Change: in `resolve_git_effect_repository` after `:122-125` and before `:129-131`, substitute
  the accepted head's identity for each non-produced revision that predates the adoption.
  `_validate_historical_source` (`commit/signature.py:365-389`) is NOT a c1 site and is not
  touched.

### b1 — the rename's shared OID is not a produced revision (WAITS on the owner)

- Call chain: `operation.py:97` `_legacy_role_result` → `branch_roles.py:349` → `:393-403`
  updates `{legacy: head→0, target: 0→head}` → `compile_observed_git_effect` → the same
  resolver.
- Today: `git_effect_observation.py:110-114` classifies `produced = revisions & {update.desired}`;
  a rename's OID is both expected and desired, so the legacy commit is read under today's reader.
- Change (only if the owner keeps the sentence): classify as produced only OIDs created by this
  effect (desired non-zero whose expected is zero), not any OID also deleted by it.

### b2 — the unshared legacy ref is refused by name

- Call chain: `rename_legacy_roles` (`branch_roles.py:335`): table at `current_head` `:348-354`,
  declared-accepted check `:357`, gaps `:359-391`, compile `:393-403`; preview `:405`, apply
  `:411` → the shape check in `role_rename.py:120-142` (`:164-201`).
- Change: one shared predicate
  `predates_adoption(root, revision, *, accepted_head, environment=None)` — no commit in
  `revision`'s history carries `binding_path("profile")` AND
  `is_ancestor(revision, accepted_head)` — used by c1 and b2 both. `rename_legacy_roles`
  adds the gap `legacy_role_rename_history_unshared:<branch>` when a legacy head neither
  predates the adoption nor shares history; a profile that existed and was dropped keeps raising
  `repository_historical_identity_invalid:.ethos/profile.toml`. The check sits before both the
  preview and the apply paths. The gap code is registered in `contracts/codes/gaps.toml`
  (owner `adapters.mutation`, the branch after the colon).

### Order and conflicts

1. a1 and c2 land in ONE commit. Without c2, a1's default policy makes the deletion of `master`
   admissible before its rename (`master` is `ROLE_OTHER` under the `work/` prefix, so a topic).
2. b1 and c1 sit in one function on the closeout path; if b1's produced classification is unfixed,
   c1 never fires for the rename's OID, so the two land together or b1's sentence stays out.
3. After a1, the reported `submit/` ref is not a legacy role ref and `prepared_deletion_gaps`
   returns `[]` for it; a2 closes the class, not that case alone.
4. c2 keys on the operation's own HEAD, not the accepted branch; a lane whose HEAD table names
   `master` therefore protects it too. A lane-root case is added to the module.

## Risks / Trade-offs

### Measured evidence

- The failing module: 14 cases, all failing on `024c217bf` and passing with the sketches; two
  (forge retirement) pass on both codes and hold today's refusal. The half-done state is built by
  a lock file on the ref so the deletion stops after the worktree removal; the same step re-run
  ends it.
- Without b1 (`probe-two-repairs-k1-b2c1.out`, 2026-11-20 16:53): `master` renames; the
  retired-schema case is the one that needs b1.

## Migration Plan

No migration: every change admits what is refused today or adds a refusal the accepted scenario
already states. A repository without a legacy table reads as before. Rollback is the revert of
this Change's commits before its landing.

## Open Questions

- b1 and its sentence of the identity requirement wait for the owner's answer (asked 2026-11-21).
  Without it the module keeps the retired-schema case out and the rename from a retired-schema
  profile stays refused.
