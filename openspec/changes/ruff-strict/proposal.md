# Proposal

## Why

The owner asked for every gate to be tightened and for the Python to meet modern practice. Ruff's
selection is broad, but whole families are unselected (Bandit, annotations, the zero-finding
guards) and preview rules apply only by exact code, so their findings stay unseen. Measured at
`5e83cfa5c` with Ruff 0.17.4, the selection below reports 214 findings: 29 `assert` statements in
product and tool code that `python -O` strips (S101), 118 missing or `Any` annotations (ANN), 39
signatures with more than five positional parameters (PLR0917), 3 product names that read as
secrets (S105) and 25 findings of ten preview rules, among them 7 float equality comparisons in
tests (RUF069).

## What Changes

- Ruff selects ERA, T10, TD, FIX, EXE, INT, PYI, S, ANN, INP, T20, ICN and PLR0917, and the
  preview rules B909, FURB118, FURB140, FURB156, PLR1714, PLR5501, RUF031, RUF056, RUF069 and
  UP052 by exact code. RUF027, RUF075, PLC2801, PLR6104 and FURB189 stay unselected: every hit is
  a false positive here, as the configuration records.
- Scoped ignores, each with its reason in the configuration: S603 and S607 everywhere (every
  subprocess passes an argv list through the process owners); S101, S105, S106, S108, S314, ANN,
  INP and PLR0917 in `tests/`; S101 in `tools/ci/delivery/acceptance/`; T20 in `tools/`; the
  per-file ignores of S314, S506, S606, S202 and ANN401 named in the design.
- The findings are fixed: asserts become typed refusals or give way to a type that holds the
  invariant, signatures gain annotations and keyword-only parameters, misleading names are
  renamed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The Ruff selection is ETHOS's own repository configuration; the shared static gate and the
paradigm's adopter checks are unchanged.

## Impact

- `.config/checks/ruff/ruff.toml` and the product, tool and test files the rules flag.
- No public behaviour changes: each refusal that an `assert` expressed keeps its condition and its
  gap, and every changed signature changes with all of its callers.
