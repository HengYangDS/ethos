# Design

## Context

The schema quality command has two legitimate responsibilities: validate every
published schema and validate real repository payloads. Its synthetic sample
builders are neither product truth nor runtime behavior; they are duplicate
fixtures embedded in production source.

## Design

`schema_validation_report()` retains schema parsing and real inputs: evolution,
docs, gates, quality profile/plan, governance profile, capability profiles,
coupling audit, and live skill activation/registry/manifests. It no longer
creates invented campaign, closeout, parity, workspace, trust, promotion, or
skill payloads.

Each removed contract remains directly checked at its natural producer boundary:
campaign closeout, shadow parity, and workspace status already validate real
payloads; campaign, trust, promotion target, activation, registry, and package
manifest validation are added to their existing owner tests. This deletes the
runtime fixture layer rather than relocating it.

Historic claim targets name real producer/test owners after deletion so evidence
topology does not retain dead implementation paths.

## Alternatives

- Move the full synthetic samples to `tests/support`: rejected; this preserves a
  parallel contract model and merely shifts code carriers.
- Keep the samples in runtime: rejected; no public behavior consumes them.

## Proof Strategy

- Focused schema, producer, skill, and claims tests.
- `ethos quality schemas`, source-budget, code-size, OpenSpec lifecycle, parity,
  and HEAD-bound proof before land.
