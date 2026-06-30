---
subject: ethos:framework-hardening-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/unit, tests/architecture, CLI smoke
---

# Framework Hardening Evidence 2026-06-30

This evidence record covers the ETHOS framework hardening batch after the
bootstrap product canonization.

Implemented scope:

- DAG validation, dependency ordering, and invalid-graph stable serialization.
- Evidence set and provenance envelope generation for `ethos prove`.
- Docs registry parsing and `ethos quality docs-registry`.
- Runner and mutation authorization contracts for land and publish readiness.
- Assistant projection commands for doctor, projection check, and MCP manifest.
- Campaign hypotheses as visible self-evolution objects.
- Expanded JSON Schemas for action validation, proof runs, evidence sets,
  provenance, docs registry, assistant projection, and mutation decisions.
- Current docs for docs registry, agent projections, runner/mutation, command
  plane, provenance, and self-evolution.
- Local SQLite state tables for events, sessions, leases, gate runs, action
  runs, evidence index, and cache entries.
- Claim evidence digest verification through `ethos quality claims`.
- Derived scorecard through `ethos report`.

Fresh validation:

```text
uv run --group dev pytest tests/unit tests/architecture -q
result: 53 passed

uv run --group dev ruff check .
result: All checks passed

uv run --package ethos ethos status --json
result: ok=true, state=dirty in work lane

uv run --package ethos ethos plan --changed --json
result: ok=true, action_graph.validation.ok=true, nodes=3

uv run --package ethos ethos prove --objective "ethos framework hardening" --json
result: ok=true, state=proven, evidence digest present

uv run --package ethos ethos report --json
result: ok=true, score=7/7

uv run --package ethos ethos assistants mcp-manifest --json
result: ok=true, resource_count=2, tool_count=4

uv run --package ethos ethos quality claims --json
result: ok=true, required_gaps=[]

uv run --package ethos ethos land --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
result: ok=true, state=land_ready

uv run --package ethos ethos publish --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
result: ok=true, state=publish_ready, remote_push=not_performed

uv build --all-packages
result: all six ETHOS packages built as sdist and wheel
```
