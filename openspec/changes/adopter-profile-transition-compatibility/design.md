# Design

## Authority boundary

The current strict `BranchRolePolicy` and schema-v2 `Commitment` remain the only
mutation and proof authorities. Compatibility belongs only in reader adapters:

1. The loose branch-role reader validates the complete deployed transition row
   shape, then discards it before constructing `BranchRolePolicy`.
2. The strict parser continues to require the current exact field set and
   rejects every transition row.
3. `load_repository_commitment` remains schema-v2-only. No global v1 model,
   dual digest resolver, or mutation fallback is introduced.

## Terminal-v1 planning projection

When normal repository Commitment loading fails, `plan` may inspect only
`.ethos/commitment.toml` through a dedicated repository-status adapter. The
adapter accepts the exact terminal-v1 field set deployed by current adopters,
normalizes omitted optional arrays to empty arrays, validates repository
identity and path scope, and returns:

- the schema-v1 semantic projection and its legacy canonical digest;
- the exact carrier SHA-256;
- explicit `mutation_authority=false` and `proof_authority=false` markers.

The command returns a passing read-only compatibility plan without embedding a
v2 `TransitionPlan`; its next action remains another reader command. `prove`,
Git-effect admission, Lease binding, and all other mutation paths continue to
call the strict v2 loader and therefore fail closed until an explicit migration
is performed.

## Package acceptance

The existing local-install smoke retains its canonical v2 lifecycle fixture and
adds one independent adopted-reader fixture. The second fixture is created from
the deployed profile and terminal-v1 Commitment shapes, then inspected by the
fresh wheel-installed binary from a source-hidden environment. Both `status`
and `plan` must pass without traceback, and the plan must prove that no proof or
mutation authority was minted.

## Rejected alternatives

- Restoring the removed transition executor would create a parallel mutation
  authority.
- Reintroducing a general v1 `Commitment` model would violate the accepted
  model-promotion cutover and allow old bytes into proof closures.
- Returning only an upgrade blocker would leave package-only `plan` unusable
  for current adopters and fail the first real-adopter acceptance criterion.
