# shadow-false-negative-gate

## Why

External ETHOS retirement requires more than a matched happy-path shadow run.
If the embedded fallback reports a blocking required gap that the external
product misses, or if the external product only reports it as advisory, the
external product is weaker and the adopter cannot retire the embedded fallback.

## What Changes

- Add a shadow parity false-negative gate: embedded blocking gaps must be a
  subset of external blocking gaps for every compared command.
- Preserve advisory external additions as accepted stricter/non-blocking
  differences, but reject external downgrades of embedded blocking gaps.
- Validate tracked shadow evidence so old evidence without false-negative
  dimension/counters no longer closes retirement parity.

## Capabilities

- `ethos-repository`: subject=shadow-false-negative-gate; reuse=extend; change=modify; facet:lifecycle=validation,runtime; facet:surface=cli,schema,docs,openspec,test,evidence; facet:authority=source,test,schema,docs,openspec,claim,evidence

## Out of Scope

- No reference adopter-specific profile migration is performed.
- No embedded fallback deletion or retirement decision is claimed complete.
- No rollback-window evidence is claimed complete by this change.

## Impact

- Strengthens adopter retirement proof without adding adopter-specific product
  roots.
- Existing parity evidence must be refreshed after this semantic dimension is
  introduced.
