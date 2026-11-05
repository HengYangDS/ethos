# Design

## Context

See [proposal.md](proposal.md). For a ref update, the prepared reference-transaction hook
(`adapters/repo/hook/admission.py`, `_prepared_reference_report`) runs these steps in order:

1. signature repair;
2. `role_rename_ref_report`, which refuses a move of a legacy role ref outside its rename;
3. `resolve_ref_move_policy`, whose absorbed-ref fallback claims the recorded `lane.retire`
   intent;
4. the role-specific admission.

The absorbed-ref retirement records its intent only when it executes, so a preview cannot call the
hook's report: every claim would find no intent.

## Goals / Non-Goals

Goals:

- A preview blocks exactly where the prepared hook would refuse for reasons that do not depend on
  the intent, with the hook's own gap.
- Deleting a legacy role ref that duplicates its successor's commit has a native route.

Non-goals:

- Changing the closeout rename, which still refuses to create a ref that exists.
- Admitting a legacy ref whose content differs from its successor's.
- Retiring alphasim's ref: that waits for its own paradigm migration.

## Decisions

1. **Shared predicates, with the claim separated.** The hook and the preview call the same two
   predicates.
   - `legacy_role_ref_protected` is the rule inside `role_rename_ref_report`.
   - `resolve_ref_move_policy(..., claim=False)` is the hook's resolution with the absorbed-ref
     fallback's intent claim left out. That claim is the one effect in the read path, and only the
     hook makes it, once the intent exists.

   `prepared_deletion_gaps` composes the two in the hook's order. The preview adds its result to
   its own gaps. This keeps one definition of each refusal, rather than a second copy of the
   conditions in the preview.

2. **A duplicate legacy ref is not a rename.** A legacy role ref is protected so that only the
   closeout rename moves it, preserving its content under the standard name. When the standard
   successor already holds the legacy ref's exact commit, deleting the legacy ref alone loses
   nothing. That deletion is admitted on its own, without renaming other legacy roles. Every other
   move stays protected.
3. **The next action names the owner.** A preview blocked by `legacy_role_ref_protected` names the
   closeout, as the hook does. One blocked by `ref_move_policy_unavailable` names
   `ethos lane status`, which reports the missing binding.

## Risks / Trade-offs

- The successor check reads the current ref at preview time. A successor that moves before the
  apply is caught by the hook itself, which re-evaluates the same predicate in its prepared phase.
