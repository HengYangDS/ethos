# Refresh-base projection regeneration

## Why

Multi-agent candidate advancement can make a Work Lane rebase conflict only on
tracked, head-bound projection evidence such as `evidence/parity/*-shadow.json`.
Treating that as a normal semantic conflict blocks an otherwise safe base refresh
and pushes agents toward manual Git resolution. Treating it as a normal success
would hide stale evidence.

## What changes

- Recognize rebase conflicts that are limited to tracked parity shadow evidence.
- Complete the Work Lane replay by keeping the candidate projection for the
  conflict path, because projection truth must be regenerated from the replayed
  repository state.
- Return `base_refreshed_projection_stale` with explicit projection refresh gaps
  and next actions instead of `refresh_base_failed` or `ready_to_land`.
- Keep all non-projection conflicts blocked as `refresh_base_failed`.

## Impact

This makes the refresh-base path closer to the kernel distinction between
repository truth and projection while preserving proof as the gate that admits
fresh evidence before landing.


## Capabilities

- `repository-governance`: subject=refresh-base-projection-regeneration; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli; facet:authority=source; facet:authority=test; facet:authority=openspec; facet:authority=evidence

## Out Of Scope

- No broad automatic conflict resolver.
- No new evidence truth store.
- No relaxation for semantic conflicts outside tracked parity shadow projections.
