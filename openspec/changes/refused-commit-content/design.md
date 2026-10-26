# Design

## Context

See [proposal.md](proposal.md).

- **Today.** `admit_reference` calls `restore_rejected_checkout_projection(root, target_head=new_value)` for every refused update in a protected checkout (`src/ethos/adapters/repo/hook/admission.py`). The restore runs `git read-tree --reset -u HEAD` when the index tree equals the target's tree and the worktree equals the index (`src/ethos/adapters/repo/worktree_effects.py`).
- **Git's order.** `git commit` writes its commit from an index that is already written, releases the index lock, and only then updates the ref. The prepared-phase hook therefore sees an index equal to the target's tree and a clean worktree. `git commit -a` still holds `index.lock` during the hook, so there the restore fails and nothing is lost.
- **Tests.** The hook tests cover a refused merge or checkout of an existing commit. The direct commit to `dev` runs only with an unavailable runtime, which fails closed before compensation, and the test does not check the staged content.

## Goals / Non-Goals

**Goals:**

- A refused operation never discards content that only it committed.
- Refused operations on existing commits keep their exact restore.

**Non-Goals:**

- Changing admission decisions or which refs are protected.
- Anything from the 0.3 design.

## Decisions

- **Containment is the ownership test.** In the prepared phase the updated ref still holds its old value. `git for-each-ref --contains <target>` therefore lists a ref exactly when the target existed before the operation. Only then did Git project it, and only then is its content still reachable after a restore.
- **The restore owns the precondition.** `restore_rejected_checkout_projection` checks containment first and returns false otherwise, as it already does for an overlay.
- **The refusal names the commit.** `admit_reference` then reports `checkout_compensation` with the state `kept` and the refused target, so the refusal names the commit.
- **Requirement text.** The requirement's sentence gains the containment condition and a scenario for a refused commit. It stays under OpenSpec's strict limit of 500 characters.

## Risks / Trade-offs

- [A refused `reset --hard` to a commit that only the reflog holds is no longer restored] → The checkout keeps that content and the refusal names the commit. Nothing is lost, and `status` shows that the checkout is not at `dev`.
- [Containment scans refs] → It runs only after a refusal in a protected checkout.
