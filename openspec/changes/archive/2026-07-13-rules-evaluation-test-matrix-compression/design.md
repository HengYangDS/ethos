# Design: Rules Evaluation Test-Matrix Compression

## Context

The four-file cluster has a 703-effective-line baseline. It mixes canonical
contract tests with repeated rule-fact envelopes and coverage-only micro-
scenarios for the same pure helpers. The duplication makes test setup
procedural and expensive to maintain.

## Decision

Use immutable test-fact declarations for stable fact envelopes and retain one
canonical helper-edge test where scenarios have heterogeneous callable shapes.
A generic pytest callable matrix was evaluated and rejected because its adapter
and type surface increased effective lines. A parameter matrix remains the
preferred representation only for partitions that produce a net deletion.

The cutover is destructive: demonstrate focused and repository coverage, then
delete redundant bodies and imports. No compatibility helper or parallel test
representation is retained.

## Invariants

1. Every former fail-closed gap is still produced by at least one canonical
   test assertion.
2. Waiver matching, fact normalization, required-gate detail filtering, and
   phase-specific rule behavior retain their public contracts.
3. The targeted test surface decreases from its 703-effective-line baseline;
   any helper must be paid for by a larger deletion in this slice.
4. The full repository coverage floor remains 100 percent.

## Risks And Mitigations

- A generic table can obscure semantics or increase code. Admit it only with a
  measured net deletion; otherwise retain the shorter named semantic test.
- A consolidation can omit a branch. Run focused coverage before deletion and
  repository coverage before proof.
- A shared fixture can become a second abstraction layer. Keep it local to the
  rules test package and delete it if it ceases to pay for itself.
