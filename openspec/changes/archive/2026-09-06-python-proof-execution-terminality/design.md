## Context

`PythonTestGate` uses pytest-xdist for bounded parallel execution. By default,
xdist restarts a worker that terminates unexpectedly and may reschedule the test
that killed it. That behavior is useful for best-effort test throughput but is
incorrect for proof: the first process loss makes the current execution
incomplete, and replaying the test no longer describes one deterministic proof
attempt.

A real subprocess probe writes an execution marker and terminates its worker
with `os._exit`. Under the default policy the marker is written repeatedly.
With `--max-worker-restart=0`, it is written once, pytest exits nonzero, and the
failure identifies the crashed worker and test.

## Goals / Non-Goals

**Goals:**

- Return one terminal failure when a pytest worker crashes or times out.
- Preserve warnings-as-errors, branch coverage, bounded parallelism,
  exact-HEAD freshness, and offline execution.

**Non-Goals:**

- No timeout increase, test skipping without semantic migration, weaker proof,
  or retry policy.
- No change to package acceptance ownership or runtime materialization; those
  have independent outcomes and owners and require separate Changes.
- No new gate, registry, state machine, or compatibility mechanism.

## Decisions

### Worker loss terminates the existing proof attempt

The existing pytest configuration owner declares `--max-worker-restart=0`.
Every invocation that selects xdist, including sharded runs, therefore inherits
the same proof semantics without duplicating policy in Python orchestration or
hosted-provider projections. Pytest accepts the option for serial invocation
without starting xdist workers.

### The regression proves behavior rather than syntax

The focused `test_python_test_gate` owner launches a nested pytest process
containing one test that writes a durable marker and then exits its worker. It
asserts nonzero pytest termination, exactly one marker write, and the concrete
worker/test diagnostic. A source-text or argument-list assertion alone would
not prove that xdist honors the intended terminal behavior.

## Risks / Trade-offs

- **Risk:** disabling worker restarts hides infrastructure instability.
  **Mitigation:** the gate preserves the original worker/test diagnostic as a
  failed proof result; it does not convert instability to success.
- **Risk:** a subprocess-only assertion could pass without exercising the gate.
  **Mitigation:** the regression constructs the real `PythonTestGate` command
  and executes it in the repository's locked test environment.

## Migration Plan

1. Add a real worker-crash regression and observe repeated execution under the
   existing default restart policy.
2. Add the no-restart option at the existing pytest configuration owner.
3. Close declarations and references, run focused proof, then exact-HEAD full
   proof once at the frozen boundary.
4. Archive and reprove, advance candidate and accepted by exact CAS, read back
   the immutable runtime, and retire the lane and owned residue.
