# Proposal

## Why

The owner asked for gates that refuse what they cannot judge. Today one gate's unexpected error
loses the run's evidence. A provider error outside seven typed exceptions escapes its gate. Any
gate's `ValueError`, including a re-raised process failure, ends the whole observation, and three
callers then drop every other gate's result. A non-`ValueError` crashes the proof. In parallel
mode the error also cancels the other gates' running commands. A provider report that JSON cannot
hold passes its gate, then fails the proof's artifact write after every gate ran. The provider seam
also turns an `unknown` failure, such as a Git timeout, into `block`.

## What Changes

- One containment rule at the provider seam and the gate seam. A timeout is `unknown` with
  `gate_timeout:<gate>`. An error that carries a decision keeps its verdict class and gaps after
  the seam's class gap. Any other `Exception` blocks with the class gap alone, and its type,
  message and raising frame are recorded. An interrupt still stops the run.
- A provider report is serialized to strict JSON inside its provider's boundary.
- A contained gate keeps the failed command's argv, exit status or bound and both streams, and a
  process failure's own evidence.
- A contained gate keeps exit code 1, so a preview never reads it as planned.
- `observe_gate_execution` moves to `ethos.application.proof.host`, beside
  `readiness_observation`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: one gate's failure refuses only that gate.

## Impact

- `adapters/gates/verification.py`, `adapters/gates/runner.py`, `application/proof/host.py`, their
  tests and the Ruff configuration (`BLE001` for the two seams).
- A failure that crashed or emptied a proof now blocks or leaves unknown only its own gate, with
  its cause recorded.
