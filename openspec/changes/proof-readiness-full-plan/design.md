# Design

## Context

See [proposal.md](proposal.md). `observe_gate_execution(root, gate_ids=...)` resolves the ids with
`selected_obligations`, and `resolve_gate_policy(root, gate_ids=tier)` adds
`quality_obligation_unproven:behavior` even without that flag, because the behavior axis's mapped
gate is not selected. `resolve_gate_policy(root, full=True)` has no such gap.

## Goals / Non-Goals

Goals:

- The readiness run executes on a real repository, not only on a replaced policy.

Non-goals:

- Changing the obligation rules. They are right for a selection that claims to prove a quality axis.
  The readiness run claims no axis.

## Decisions

- **Run from the full policy.** The readiness run takes `policy.nodes` and `policy.registry` from
  the full resolution, filters the nodes to `readiness_tier`, and runs them with
  `run_gate_graph` and `LocalGateRunner`. It checks the head and execution source before and after,
  as the host observation does.
- **A real-repository test.** A test runs the readiness verb against a governed fixture repository
  without replacing policy resolution, so a regression of this kind fails.

## Risks / Trade-offs

- The run duplicates a few lines of the host observation's source binding. It stays in `host.py`,
  because `runner.py` is at its size ceiling.
