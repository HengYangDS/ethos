# Design

## Context

See [proposal.md](proposal.md). `render_allure` counts the `fullName` of every Allure result and
compares the count with the names it derives from the report log's setup reports. allure-pytest
2.16.2 computes `fullName` in `allure_full_name(item)` as `<package><.classes>#<test>`, where the
package and classes come from `ParsedPytestNodeId(item.nodeid)` and the test is `item.originalname`
for a function item. The derivation in `_allure_name` uses
`ParsedPytestNodeId(nodeid).test_function` instead, which agrees with `item.originalname` unless a
parameter id contains `::`.

## Goals / Non-Goals

**Goals:**

- Admission and Allure name every case alike, for every valid parameter id.
- A refusal says which cases differ.

**Non-Goals:**

- Correcting allure-pytest's own `fullName` for such cases; that is upstream's to fix.
- Running every failure to the end. The accepted requirement "Test failure bounds pending
  verification work" stops pending work at the first failure; the serial discovery it causes on
  hosted runs is answered by running hosted checks in the local proof, through probe rows
  (`hosted-once`), and by verifying the proposal head before landing.

## Decisions

- **Mirror the producer's rule exactly.** The derived name uses allure-pytest's parser for the
  package and classes, as `allure_full_name` does, and the original function name, taken from the
  node identity before its first `[`. Rejected: matching by the hidden `pytest_nodeid` parameter
  that `tests/conftest.py` adds, because a case skipped before its fixtures run carries none (3 of
  7,782 in the proposal run); explicit parameter ids without `::`, which treat one symptom while any
  other valid id breaks again; patching allure-pytest, which modifies vendor source.
- **Name the difference.** The refusal appends up to three missing and three unexpected names, so
  the hosted receipt explains itself.

## Risks / Trade-offs

- [allure-pytest changes its naming rule] → The architecture case with a `::` parameter fails, and
  the mirror follows the new rule.
