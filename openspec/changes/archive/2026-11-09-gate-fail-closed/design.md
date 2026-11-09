# Design

## Context

Two seams run untrusted work. `provider_reports` (`adapters/gates/verification.py`) calls each
provider of a gate. `_run_ready_gate` (`adapters/gates/runner.py`) runs one gate once its
prerequisites are settled. `observe_gate_execution`, `readiness_observation` and `_prove` catch
`ValueError` around the whole graph, so one gate's error stands for the whole run. A committee
review (scratch `gates-review/`) settled the decisions below.

## Goals / Non-Goals

Goals: every failure of one provider or gate becomes that gate's outcome with its cause, and the
rest of the run keeps its evidence.

Non-Goals: an empty selection that passes vacuously, such as `shell-lint` over ETHOS's zero shell
files. That is `gate-applicability`, which binds `asset_classes` to path patterns and adds
`not_applicable` after a census of the governed repositories, since their gate declarations share
the kernel schema.

## Decisions

1. **One rule, one function.** `failure_part(error, *, class_gap, timeout_gap)` returns a verdict
   class and gaps:
   - `subprocess.TimeoutExpired` gives `unknown` with the timeout gap;
   - an `OutcomeError` keeps its verdict class, with the class gap first and then its own gaps;
   - any other `Exception` gives `block` with the class gap alone, because a message is not a gap.

   The diagnostic's `error` field records the type, the message and the raising frame.
   `BaseException` propagates.

2. **Provider seam.** `except Exception` replaces the typed tuple. The report is serialized once
   to strict JSON inside the boundary, so a report that cannot be recorded fails its own provider;
   the report itself is kept as returned.
3. **Gate seam.** Everything after the dependency hold is contained: the run, the deadline lookup
   and the timing. A contained result keeps exit code 1, because a preview reads a missing exit code
   as a planned check. Dependents see an unproven prerequisite and inherit its class. The cause
   keeps a failed command's outcome and a process failure's evidence, as native command failures
   do elsewhere.
4. **Whole-run boundaries stay.** The callers' `ValueError` boundaries still cover invalid plans,
   foreign providers, policy resolution and source observation.
5. **Placement.** `observe_gate_execution` resolves policy, observes the source, runs the graph and
   composes the outcome, which is application work. It moves to `application/proof/host.py`. That
   also keeps `runner.py` within the per-file ceiling.
6. **Lint.** Ruff's `BLE001` is ignored for the two seam modules only, with the reason in the
   configuration.

## Risks / Trade-offs

- An `AssertionError` raised inside a test double is now contained. Tests assert after the run, not
  inside doubles.
