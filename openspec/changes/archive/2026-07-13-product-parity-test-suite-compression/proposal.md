# Product-Parity Test-Suite Compression

## Why

The product-parity suite repeats payload envelopes, evidence-file setup, and the
same assertion shape across finite accepted-difference and projection partitions.
The repetition inflates the executable test surface without adding independent
contract coverage.

## What Changes

- Centralize test-only payload and evidence-file envelopes without moving parity
  behavior into fixtures.
- Express uniform accepted-difference and projection-normalization partitions as
  declarative pytest case tables with domain-named identifiers.
- Keep named tests for false-negative, process-failure, schema, and integration
  boundaries; delete only superseded setup and runner bodies.

## Out Of Scope

- Shadow execution, parity evidence persistence, acceptance semantics, and CLI
  behavior.
- Any reduction in the 100-percent line and branch coverage floor.

## Capabilities

- `quality`: subject=product-parity-test-compression; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence
