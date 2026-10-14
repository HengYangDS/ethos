## Why

The first ETHOS-governed landing of web-ingestion-benchmark advanced its candidate, but `land --closeout` blocked with `accepted_policy_unavailable`. Closeout reads the incumbent accepted head's `[branch_roles]` table strictly, recognizing only the predecessor schema that lacks `canonical_sibling_worktrees`. The adopter's table predates `release_mirror` as well. It is a complete declaration of its own schema generation, so the incumbent roles are known but cannot be read, and the accepted branch can never advance.

Before the adopter declared its complete table, its candidate update also failed with an opaque `pydantic` pattern error. Without a strict table, ref movement used the product default roles, the adopter's candidate branch matched none of them, and the empty operation reached the ref intent model.

## What Changes

- An incumbent branch-role table that predates `canonical_sibling_worktrees`, or both that field and `release_mirror`, is read with those fields' predecessor defaults: no canonical sibling worktrees, and an independent release mirror. These are the meanings the lenient reader has always assigned. Every other incomplete or unknown table is still rejected.
- The opt-in is renamed from `allow_legacy_sibling_default` to `allow_predecessor_defaults`, because it now covers two predecessor generations. Its two callers, accepted closeout and lease control-root selection, keep reading only incumbent provenance.
- A candidate-integration ref move whose ref matches no declared role fails with `ref_transition_operation_unresolved:<ref>` before any ref intent is written.

## Impact

- Code: `src/ethos/contracts/branch/roles.py`, `src/ethos/adapters/mutation/accepted/admission.py`, `src/ethos/adapters/mutation/lane_lifecycle/lease/acquisition.py` and `src/ethos/adapters/repo/git_effects.py`.
- Tests: the branch-role contract gains the older predecessor, accepted closeout reads it from a committed incumbent, and a landing regression reproduces the adopter's failed candidate update, which now names the unresolved ref.
- Specs: repository-governance gains two requirements.
- Consumers: adopters whose incumbent table predates `release_mirror` can close out without first replacing their accepted head. Repositories with a current table are unaffected.
