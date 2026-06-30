---
subject: ethos:work-lane-admission-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/unit, CLI smoke, OpenSpec
---

# Work Lane Admission Evidence 2026-06-30

This evidence record covers the Work Lane admission hardening batch.

Implemented scope:

- `ethos status` and `ethos lane status` classify linked worktrees and report
  foreign `work/*` lanes from git worktree metadata.
- `ethos lane prewrite` blocks tracked writes from protected roots and admits
  writes only from the current owned Work Lane with matching editor root.
- `ethos lane prewrite` rejects tracked writes in a `work/*` lane when
  editor-root binding is missing.
- `ethos lane start --apply` creates a `work/*` linked worktree from a clean
  accepted root and records an ignored local SQLite lease.
- `ethos lane start --apply` rejects existing `work/*` lanes and dirty accepted
  roots with `lane_start_requires_clean_accepted_root`.
- `ethos land --apply` and `ethos publish --apply` reject protected roots even
  when authorization and expected HEAD are supplied.
- Apply-mode admission is evaluated before product self-audit, so non-ETHOS
  target repositories receive structured blocked JSON instead of schema-file
  crashes.

Fresh validation:

```text
uv run --group dev pytest tests/unit/test_workspace_lanes.py tests/unit/test_workspace_state.py tests/unit/test_workspace_apply.py tests/unit/test_cli_contracts.py tests/unit/test_docs_registry.py tests/unit/test_command_registry_depth.py -q
result: 52 passed

uv run --group dev pytest -q
result: 124 passed

uv run --group dev ruff check .
result: All checks passed

git diff --check
result: clean

uv run --package ethos ethos lane status --json
result: ok=true, role=work_lane, foreign_work_lane_count=1, required_gaps=["foreign_work_lane_present"]

uv run --package ethos ethos lane prewrite README.md --editor-root /Users/yheng/.config/superpowers/worktrees/ethos/work-lane-admission --require-editor-root --json
result: ok=true, state=admitted

uv run --package ethos ethos status --json
result: ok=true, state=dirty, required_gaps=["foreign_work_lane_present"]

uv run --package ethos ethos report --json
result: ok=true, score=14/14

openspec validate --all --strict --json
result: 9 passed
```
