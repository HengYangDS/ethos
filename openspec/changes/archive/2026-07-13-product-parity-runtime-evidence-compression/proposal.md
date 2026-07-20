# Product-Parity Runtime/Evidence Test Compression

## Why

The remaining product-parity runtime, tracked-evidence, and report tests repeat
Git repository construction, Work-Lane checkout/lease setup, inert shadow
reports, and public evidence assertions. The repetition enlarges the executable
test carrier without adding independent behavior, delaying the global
source-budget settlement.

## What Changes

- Consolidate only uniform test setup and exact public-output partitions for
  shadow runner, evidence-writing, and tracked-evidence report behavior.
- Move test-only Git/lease setup and inert shadow payload constructors into the
  existing parity snapshot fixture module.
- Use declarative pytest tables only where cases share the same operation and
  assertion contract; retain named tests for protected-write, process-failure,
  backend, and freshness boundaries.
- Delete the superseded setup/assertion bodies and prove a net reduction across
  `test_runners.py`, `test_evidence_writing.py`, and `test_report.py`.

## Capabilities

- `quality`: subject=product-parity-runtime-evidence-test-compression; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=test,openspec,evidence; facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- No production parity, routing, shadow-execution, CLI, or evidence semantics
  change.
- No weakening of 100-percent line/branch coverage or repository quality gates.
- No test DSL that reproduces product classification or normalization.
