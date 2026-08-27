## Why

The public result boundary currently permits `unknown` and `block` without a
named missing fact, failed condition, or adverse diagnostic. `lane status` also
reduces a raw workspace-facts mapping as though it were an independently owned
verdict, so a healthy lane can be projected as `unknown` with no gaps.

## What Changes

- Require every non-pass public result to carry a concrete reason.
- Keep `EthosResult` as the sole public validator; do not change internal
  decision rationale or add another result model.
- Derive `lane status` from workspace validation and its explicit gaps instead
  of inventing a verdict from a facts-only mapping.
- Migrate tests that construct reasonless non-pass values and retain exact
  reason codes.

## Out of Scope

No authority resolver, recovery command, diagnostic ontology, persistent
continuation, compatibility reader, or TransitionPlan redesign is introduced.
Those require separate evidence and a successor Commitment.
