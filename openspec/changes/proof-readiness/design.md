# Design

## Context

See [proposal.md](proposal.md). `run_plan_checks` in `src/ethos/surface/cli/root/proof.py`
already splits a full plan with `readiness_tier` and runs that tier before admission.

## Goals / Non-Goals

Goals:

- One native command runs the same gates a full proof would run before admission.

Non-goals:

- A new gate selection rule. The tier is the one `readiness_tier` already defines.
- A proof attestation. A readiness run proves nothing about the test and package gates.

## Decisions

- **A mode of the host observation, not of the proof.** `observe_gate_execution` in
  `src/ethos/adapters/gates/runner.py` already runs gates without granting proof authority, writes
  no attestation, and binds the exact head with `--expect-head`. `--readiness` resolves the full plan
  there and runs only the nodes of `readiness_tier`, so the tier and a full proof cannot disagree.
- **Not run is reported, never passed.** Every planned test or package gate appears in the result
  as `not_run`. The verdict passes only when every readiness gate passes.
- **No admission.** The tier does not need the proof slot or host load. A full proof runs it before
  admission too.
- **Entry point.** `ethos prove --readiness --execute` takes the same `--expect-head` binding. It is
  incompatible with `--gate`, `--change` and `--host`, because it always uses the full plan.

## Risks / Trade-offs

- Its output looks like a proof result. The `readiness` mode, the `not_run` gates and the missing
  attestation keep the two apart.
