## Why

Current Work Lane authoring authority is interpreted twice. Exact prewrite
admission trusts the fresh Lease-bound Commitment, while status and planning can
also require historical start, rebind, or archive Attestations. The same current
coordinates can therefore be writable through the guard yet reported as
change_generation_authority_missing.

## What Changes

- Make one fresh Lease-bound Commitment resolution the owner of current
  authoring authority.
- Make status, plan, prewrite, and pre-commit project that same resolution.
- Keep transition Attestations only as provenance for historical path
  attribution and effect verification.
- Delete current-authority blockers inferred from missing historical transition
  evidence and delete closeout-derived authoring guesses.

## Out of Scope

Transaction recovery, unbound-lane reconciliation, proposal-ref semantics,
archive lifecycle redesign, and Commitment succession remain dependency-ordered
successors.
