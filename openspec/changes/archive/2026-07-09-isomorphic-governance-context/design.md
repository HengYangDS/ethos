# Design

## Context

The official OpenSpec boundary is the change carrier and accepted spec delta.
The ETHOS product boundary is the command result envelope, schema, tests, docs,
and evidence that make the governed-repository context visible without turning
OpenSpec or any provider surface into the product command plane.

## Design

`EthosResult` gains an optional top-level `governance_context` field. Primary
root commands populate it from `ethos.repository.context.context_for_root`, which
selects the `product` profile for the ETHOS product repository and otherwise uses
the detected adoption profile. The context itself still has one subject kind:
`repository`.

This keeps the shared kernel in one place and avoids command-specific heuristics:
`status`, `plan`, `prove`, `land`, `publish`, `orient`, and `report` all expose
the same transition command semantics at the same result-envelope location.
Nested domain reports may continue to carry their own context when already
present, but pure data contracts do not receive envelope metadata. In particular,
`status.data` remains the workspace-status payload validated by
`workspace-status.schema.json`.

## Alternatives

Adding `governance_context` into every command-specific `data` payload was
rejected because it would mix envelope metadata with native data contracts and
force schema churn into unrelated domains. Adding a new governance command was
rejected because the existing primary command plane already owns the transition
loop and reader views.

## Proof Strategy

- CLI contract tests assert every primary command has top-level
  `governance_context` for product and adopted repositories.
- Schema tests assert the result envelope accepts the governed-repository
  context while preserving the existing result shape.
- Status tests assert `status.data` does not contain the envelope context.
- OpenSpec lifecycle, claims, report, and head-bound proof close the carrier.
