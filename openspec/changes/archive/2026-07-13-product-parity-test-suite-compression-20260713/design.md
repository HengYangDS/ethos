# Design: Product-Parity Test-Suite Compression

## Context

`snapshots.py`, `test_semantics.py`, `test_projection_semantics.py`, and
`test_gaps.py` contain a 1,483-effective-line corpus. Most examples differ only
by declarative command facts, evidence placement, and expected public output,
yet each carries a separate Python setup and assertion sequence.

## Decision

Use canonical fixture constructors only for inert payload and evidence-file
setup. Use pytest parameterization only for cases sharing the same operation and
exact observable assertion. Case tables contain literal data; no callback,
dynamic test DSL, or reimplementation of product classification is admitted.
Tests that own a distinct error, false-negative, schema, or integration boundary
remain named.

The cutover is destructive: prove focused behavior and coverage, delete the old
bodies, then prove the repository at the resulting HEAD.

## Invariants

1. Every accepted-difference kind and normalized projection contract remains
   directly asserted.
2. False-negative, process-failure, schema, and integration boundaries retain
   independent diagnostic tests.
3. The scoped test surface is smaller than the 1,483-effective-line baseline.
4. Product parity runtime behavior and public JSON stay unchanged.

## Risks And Mitigations

- A broad table can hide failing semantics. Use domain-named case identifiers
  and retain separate error-boundary tests.
- A fixture can duplicate product behavior. Restrict it to literal envelope and
  public-output facts; it must not classify or normalize a product payload.
- Parameterization can add rather than remove code. Reject any table whose
  measured representation is not a net deletion.
