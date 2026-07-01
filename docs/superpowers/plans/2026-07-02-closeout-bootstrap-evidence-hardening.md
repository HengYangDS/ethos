---
subject: ethos:plan:closeout-bootstrap-evidence-hardening
role: execution-plan
state: active
relations:
  change: ethos-closeout-bootstrap-evidence-hardening
---

# Closeout Bootstrap Evidence Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden ETHOS local closeout, parity evidence, shadow backend, and coordination reporting while removing current-surface residue from retired closeout flows.

**Architecture:** Keep Git as the required repository substrate and OpenSpec as a mandatory governance dependency, but express product behavior through vendor-neutral `ethos ...` JSON packages. Add machine-readable next-action packages for closeout bootstrap and parity refresh, surface selected shadow backends explicitly, and split coordination gaps from blocking gaps.

**Tech Stack:** Python 3.12, Typer CLI, JSON Schema contracts, pytest, Ruff, uv, Git worktrees, OpenSpec validation.

---

### Task 1: Closeout Bootstrap Package

**Files:**
- Modify: `tests/unit/test_cli_contracts.py`
- Modify: `packages/ethos/src/ethos/cli.py`
- Modify: `docs/reference/command-plane.md`
- Modify: `docs/architecture/runner-and-mutation.md`

- [ ] **Step 1: Write failing test for closeout bootstrap guidance**

Add a test near the existing `land --closeout` tests asserting `ethos land --closeout --json` includes a `closeout_bootstrap` package with:

```python
bootstrap = payload["data"]["closeout_bootstrap"]
assert bootstrap["kind"] == "closeout_bootstrap"
assert bootstrap["accepted_root"] == repo.resolve().as_posix()
assert bootstrap["audit_root"] == candidate.resolve().as_posix()
assert bootstrap["candidate_branch"] == "candidate/dev"
assert bootstrap["accepted_branch"] == "dev"
assert bootstrap["command"] == (
    f"ethos land --closeout --apply --authorize --expect-head {accepted_head} "
    f"--root {repo.resolve().as_posix()} --json"
)
assert bootstrap["blocking"] is False
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_cli_contracts.py::test_land_closeout_exposes_bootstrap_package_for_current_runner -q
```

Expected: FAIL because `closeout_bootstrap` is missing.

- [ ] **Step 3: Implement closeout bootstrap package**

Add a helper in `packages/ethos/src/ethos/cli.py` that builds the command from the accepted root and configured branch policy, then include it in the `land --closeout` data payload. The helper must not run Git mutation by itself.

- [ ] **Step 4: Run GREEN**

Run:

```bash
uv run --group dev pytest tests/unit/test_cli_contracts.py::test_land_closeout_exposes_bootstrap_package_for_current_runner -q
```

Expected: PASS.

- [ ] **Step 5: Update closeout docs**

Document that accepted-root bootstrap should run a current ETHOS runner against `--root <accepted-root>` and that raw `git merge --ff-only candidate/dev` is not the product mechanism.

### Task 2: Parity Evidence Refresh Package

**Files:**
- Modify: `tests/unit/test_parity_command.py`
- Modify: `packages/ethos-repository/src/ethos_repository/parity.py`
- Modify: `packages/ethos/src/ethos/cli.py`
- Modify: `docs/governance/capability-parity-ledger.md`

- [ ] **Step 1: Write failing tests for concrete evidence refresh**

Extend stale and target-mismatch parity tests to assert each invalid evidence execution package includes:

```python
refresh = payload["data"]["evidence"]["refresh_package"]
assert refresh["kind"] == "parity_evidence_refresh"
assert refresh["adopter"] == "sample-adopter"
assert refresh["target"] == target.resolve().as_posix()
assert refresh["command"] == (
    f"ethos parity shadow --adopter sample-adopter --target {target.resolve().as_posix()} "
    "--execute --write-evidence --json"
)
assert refresh["blocking"] is True
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_parity_command.py::test_parity_gaps_recommends_write_evidence_when_tracked_evidence_is_stale tests/unit/test_parity_command.py::test_shadow_parity_report_rejects_target_head_mismatch -q
```

Expected: FAIL because refresh package is absent or generic.

- [ ] **Step 3: Implement refresh package builder**

Add a public helper in `ethos_repository.parity` that returns a concrete `parity_evidence_refresh` package for missing, stale, target-mismatch, or invalid evidence. Use actual adopter and target when known; keep placeholder text only when no target exists.

- [ ] **Step 4: Run GREEN**

Run the same focused tests. Expected: PASS.

- [ ] **Step 5: Update parity ledger docs**

Clarify that tracked shadow evidence is closeout input only when product head, target head, command digest, target path, and capability basis are fresh. Invalid evidence must point at `ethos parity shadow --adopter <name> --target <path> --execute --write-evidence --json`.

### Task 3: Shadow Backend Selection Profile

**Files:**
- Modify: `tests/unit/test_parity_command.py`
- Modify: `packages/ethos-adapters/src/ethos_adapters/shadow.py`
- Modify: `schemas/ethos/shadow-parity.schema.json`
- Modify: `docs/governance/capability-parity-ledger.md`

- [ ] **Step 1: Write failing backend metadata tests**

Update pixi, uv, and missing-backend tests to assert embedded results include:

```python
assert result["backend"]["kind"] == "pixi"  # or "uv-workspace", "missing"
assert result["backend"]["command"] == "pixi run ethos status --json"
assert result["backend"]["blocking"] is False
```

For missing backends, assert `blocking` is `True` and `required_gaps` contains `embedded_backend_missing`.

- [ ] **Step 2: Run RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_parity_command.py::test_parity_shadow_execute_reports_missing_embedded_backend tests/unit/test_parity_command.py::test_embedded_shadow_runner_accepts_pixi_pyproject_workspace tests/unit/test_parity_command.py::test_shadow_embedded_runner_accepts_uv_workspace -q
```

Expected: FAIL because backend metadata is missing.

- [ ] **Step 3: Implement explicit backend selection**

Replace hidden command selection with a helper returning `{"kind", "command", "required_gaps", "blocking"}`. Keep supported backends `pixi` and `uv-workspace`; report missing backends as `embedded_backend_missing` instead of ambiguous fallback text.

- [ ] **Step 4: Run GREEN**

Run the focused backend tests. Expected: PASS.

### Task 4: Coordination Gap Presentation

**Files:**
- Modify: `tests/unit/test_workspace_lanes.py`
- Modify: `packages/ethos-adapters/src/ethos_adapters/status.py`
- Modify: `schemas/ethos/workspace-status.schema.json`

- [ ] **Step 1: Write failing coordination package test**

Extend foreign lane tests to assert:

```python
coordination = status["coordination"]
assert coordination["blocking"] is False
assert coordination["required_gaps"] == []
assert coordination["advisory_gaps"] == status["coordination_gaps"]
assert coordination["foreign_work_lane_count"] == 1
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_workspace_lanes.py::test_workspace_status_reports_foreign_work_lanes_without_reading_them -q
```

Expected: FAIL because `coordination` is missing.

- [ ] **Step 3: Implement coordination package**

Add `coordination` to workspace status JSON. Keep existing `coordination_gaps` for compatibility, but make the product semantics explicit: foreign lanes are advisory unless they affect the current lane's closeout support.

- [ ] **Step 4: Run GREEN**

Run the focused workspace test. Expected: PASS.

### Task 5: Clear Current-Surface Residue

**Files:**
- Modify: `tests/unit/test_command_registry_depth.py`
- Modify: `docs/superpowers/plans/2026-07-01-ethos-mechanism-hardening.md`
- Modify: `docs/superpowers/plans/2026-07-01-asset-quality-kernel.md`
- Modify: `docs/superpowers/plans/2026-07-02-ethos-closeout-and-evidence-seal.md`

- [ ] **Step 1: Write failing residue scan**

Add a test that scans active `docs/superpowers/plans/*.md` and rejects:

```python
("raw accepted-root git merge", "old named closeout argument")
```

- [ ] **Step 2: Run RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_command_registry_depth.py::test_current_plan_docs_do_not_contain_retired_closeout_mechanisms -q
```

Expected: FAIL on the two stale plan documents.

- [ ] **Step 3: Clean residue**

Replace stale closeout snippets with current `ethos land --apply`, `ethos land --closeout --apply --authorize --expect-head ... --root ...`, and `ethos lane retire-landed --branch ... --apply` flows. Mark previously completed closeout task residue as complete if the file is still a current plan.

- [ ] **Step 4: Run GREEN**

Run the focused residue scan. Expected: PASS.

### Task 6: Focused and Broad Verification

**Files:**
- No production file changes unless gates expose regressions.

- [ ] **Step 1: Run focused tests**

```bash
uv run --group dev pytest tests/unit/test_cli_contracts.py::test_land_closeout_exposes_bootstrap_package_for_current_runner tests/unit/test_parity_command.py::test_parity_gaps_recommends_write_evidence_when_tracked_evidence_is_stale tests/unit/test_parity_command.py::test_shadow_parity_report_rejects_target_head_mismatch tests/unit/test_parity_command.py::test_parity_shadow_execute_reports_missing_embedded_backend tests/unit/test_workspace_lanes.py::test_workspace_status_reports_foreign_work_lanes_without_reading_them tests/unit/test_command_registry_depth.py::test_current_plan_docs_do_not_contain_retired_closeout_mechanisms -q
```

- [ ] **Step 2: Run unit/architecture suites**

```bash
uv run --group dev pytest tests/unit tests/architecture -q
```

- [ ] **Step 3: Run static and governance gates**

```bash
uv run --group dev ruff check .
uv run --package ethos ethos quality docs --json
uv run --package ethos ethos quality command-examples --json
uv run openspec validate --all --strict --json
uv run --package ethos ethos playbooks check --mode v2-strict --json
uv run --package ethos ethos report --json
```

- [ ] **Step 4: Refresh parity evidence if product HEAD changed evidence requirements**

Run generic and alphasim shadow evidence refresh only if the earlier gates report stale or invalid tracked evidence. Do not target retired worktree paths.

- [ ] **Step 5: Run final proof**

```bash
uv run --package ethos ethos prove --full --execute --expect-head "$(git rev-parse HEAD)" --json
```

### Task 7: Local Closeout

**Files:**
- Commit tracked changes from this lane only.

- [ ] **Step 1: Commit lane changes**

```bash
git add docs packages schemas tests
git commit -m "Harden closeout bootstrap and parity evidence"
```

- [ ] **Step 2: Land to candidate**

```bash
uv run --package ethos ethos land --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
```

- [ ] **Step 3: Fast-forward accepted root through ETHOS closeout**

```bash
uv run --package ethos ethos land --closeout --apply --authorize --expect-head "$(git -C /Users/yheng/projects/ethos rev-parse HEAD)" --root /Users/yheng/projects/ethos --json
```

- [ ] **Step 4: Retire only this lane**

```bash
uv run --package ethos ethos lane retire-landed --branch work/closeout-bootstrap-evidence-hardening --apply --root /Users/yheng/projects/ethos --json
```

---

## Self-Review

- Spec coverage: closeout bootstrap, parity evidence refresh, shadow backend selection, coordination advisory shape, residue cleanup, verification, and local closeout are covered.
- Placeholder scan: `<repo>`, `<name>`, and `<path>` appear only where the product intentionally cannot know a target before the user supplies one.
- Type consistency: new package names are `closeout_bootstrap`, `parity_evidence_refresh`, `embedded_backend`, and `coordination`; all are JSON dictionaries consistent with existing ETHOS package shapes.

Status: active execution plan for the local closeout hardening lane.

Purpose: define the implementation, verification, evidence refresh, and local
closeout steps for closeout bootstrap and parity evidence hardening.

See also: [Command Plane](../../reference/command-plane.md),
[Runner And Mutation](../../architecture/runner-and-mutation.md), and
[Capability Parity Ledger](../../governance/capability-parity-ledger.md).
