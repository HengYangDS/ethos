# Design

## Context

`resolve_git_effect_repository` owns the single bounded v1-to-v2 repository
identity transition. Candidate landing already supplies its required exact
prestate ID and byte digest. Accepted closeout supplied only the bootstrap flag,
which left the same transition unsatisfiable at the next ref boundary.

## Decision

When the accepted HEAD cannot be loaded as v2, accepted closeout validates that
exact revision with `terminal_v1_binding` and projects its ID and byte digest
into the existing Git-effect policy. A normal v2 accepted HEAD uses the unchanged
path. Shared Git-effect admission remains the sole validator.
