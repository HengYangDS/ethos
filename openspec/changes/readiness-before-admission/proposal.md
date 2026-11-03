# Proposal

## Why

A full executing proof waits for its repository's proof slot and for host load before its first
gate runs. Only then do its readiness gates run: every gate that is neither a test nor a package
gate. The test and package gates already wait for them and do not start when one fails, so a
readiness failure costs the whole admission wait, though the gates take about a minute.

- On 11-03 the `ruff-docstrings` proof waited 871.6 s for admission. Its 28 readiness gates then
  finished within 67 s of their start; only `unit-architecture` (1,353 s) and `local-install-smoke`
  (683 s) ran long.
- On 11-02 and 11-03 two full proofs failed within a minute of admission. A lane's Mise lacked a
  locked tool after a supply move, and a deleted declaration field left the `docker` reference
  without an owner. In the period before, three more did the same, on dependency hygiene, module
  layout and the archive simulation.
- Every admission wait also holds other sessions' heavy work on the shared host: the operator
  announces the proof, and peers hold their renders and proofs until it ends.

## What Changes

- A full executing proof runs its readiness gates before it waits for the proof slot and host load.
- When a readiness gate fails, the proof ends without waiting. Its test and package gates report
  `gate_dependency_not_proven`, as they do today, and do not run.
- When every readiness gate passes, the proof waits for admission once and runs the remaining
  gates. No gate runs twice, and one proof result keeps every gate's evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a full executing proof runs its readiness gates before host-load admission.

## Impact

`src/ethos/surface/cli/root/proof.py` (`run_plan_checks`, `prove`), `src/ethos/adapters/gates/runner.py`
(the readiness tier and gate graphs with settled results), the module docstring of
`src/ethos/adapters/gates/proof_slot.py`, `docs/reference/command-plane.md` and the proof scheduling
tests. Gate declarations, the membership of the readiness tier and the admission parameters do not
change.
