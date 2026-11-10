# Proposal

## Why

Nothing ties a gate to the test that proves it refuses what it exists to refuse. A rename or a
deletion of either loses that proof silently. A skipped refusal test passes vacuously. An
inventory of the 35 gate ids at `bd0edc28c` found:

- planted refusal tests for 23;
- only mocked or indirect refusals for 11;
- none for 2.

## What Changes

- A `gate(id, role)` pytest marker, registered by its plugin, declares the gate and the role a test
  proves: `refusing`, `conforming` or `fail_closed`.
- A test plugin refuses an unregistered id or role at setup and fails any marked test that skips
  or xfails. It records each mark in the test's report properties.
- An architecture test keeps an explicit ledger of credited (gate, role) pairs. On a whole-suite
  run, every credited pair needs a passing marked test, and every marked test needs a credited
  pair. A pair is credited only after one recorded mutant of the gate's policy makes its refusing
  test fail.
- First slice: `commit-ranges` and `format-selection` in all three roles.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: each gate's efficacy is proven by marked tests in a ledger that only grows.

## Impact

- `tests/conftest.py`, a new `tests/support/gate_marks.py` that registers the marker,
  a new `tests/architecture/test_gate_efficacy.py`, and the marked tests.
- Test runs fail on a skipped marked test or an unregistered mark; no product behaviour changes.
