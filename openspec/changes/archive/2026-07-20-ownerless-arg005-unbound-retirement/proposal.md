## Why

`work/arg005-coverage-edges-20260719` is a duplicate unbound accepted-ancestor
residual. It contains no operational value beyond a historical parity refresh
already absorbed by later accepted history. Leaving it open preserves a dead
ref, while deleting it without exact authority would be unsafe.

## What Changes

- Record exact graph-backed absorption for one clean, lease-free, unbound ARG005
  source ref.
- Bind one accepted Claim and Chronicle to a later native
  `lane retire unbound` transition for that target only.
- Require exact head, accepted policy bytes, authorization, break-glass,
  irreversible confirmation, re-observation, compare-and-delete, and receipt.
- Retire this temporary carrier after the target receipt exists.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=ownerless-arg005-unbound-retirement;
  reuse=extend; change=modify; facet:lifecycle=retirement;
  facet:surface=openspec,claim,chronicle,docs;
  facet:authority=source,graph,evidence,native-command.

## Out Of Scope

- Any target other than `work/arg005-coverage-edges-20260719` at its exact
  observed head; `work/skill-scripts-ruff-20260719`; an active lease; raw
  deletion; worktree reconstruction; protected branches; remote or hosted CI
  mutation; and publication.
