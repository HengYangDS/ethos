## Why

The Python proof graph runs pytest through xdist. When a timeout or process
failure terminates a worker, xdist's default recovery restarts a worker and may
replay the lost test inside the same proof attempt. A proof attempt must not
silently turn one unknown or failed execution into repeated executions.

## What Changes

- Make a crashed or timed-out pytest worker terminal for the current test gate;
  do not restart a worker and replay its test inside the same proof.
- Prove the behavior with a real crashed worker, not only by inspecting command
  text.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: worker loss terminates one Python proof attempt without replay.

## Impact

The Change is bounded to the existing Python test gate and its focused
regression. It introduces no cache, registry, timeout increase, retry wrapper,
compatibility path, or persistent state. It does not modify package/runtime
materialization, adopter repositories, or the full proof floor.
