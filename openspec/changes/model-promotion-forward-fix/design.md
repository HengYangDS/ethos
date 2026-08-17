# Design

## Authority selection

Publication is a repository-level effect. The command loads the repository
Commitment from the exact accepted HEAD and asks the existing proof resolver for
that authority before mutable Lease-generation checks or conflict evaluation.
Historical proofs remain immutable and queryable. Proofs with another
Commitment are inapplicable; conflicts within the selected authority still fail
closed.

## Locked runtime closure

The source checkout remains the sole build input. After building the ETHOS
wheel, runtime materialization asks the project's existing `uv.lock` to supply
the complete offline install closure instead of resolving dependencies from the
wheel metadata. The lock is not copied into a second policy, and installed-wheel
runtime materialization remains unchanged.

## Failure boundaries

- A missing or wrong repository Commitment cannot authorize publication.
- Same-authority stale bindings and contradictions remain blockers.
- A missing or unusable lock fails runtime materialization; it never falls back
  to unlocked resolution or network access.
- No new entity, compatibility branch, proof mutation, or dependency pin is
  introduced.

## Verification

Focused tests reproduce publication after Work Lane retirement and inspect the
exact `uv` install invocation. Existing proof-conflict and package-only runtime
tests remain the negative contract. Final acceptance includes source-independent
AIGW and Proxy `status`/`plan` probes and independent remote publication.
