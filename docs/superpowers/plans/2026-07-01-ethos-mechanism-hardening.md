---
subject: ethos:plan:mechanism-hardening
role: execution-plan
state: active
relations:
  governs: ethos-mechanism-hardening
---

# ETHOS Mechanism Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

Status: active.

Purpose: define the implementation and verification path for hardening ETHOS lifecycle entry, branch-role configuration, command-plane boundaries, and binding classifications without remote publication or mutations outside this Work Lane.

See also: [Runner And Mutation](../../architecture/runner-and-mutation.md), [Product Design Contract](../../governance/product-design-contract.md), and [Command Plane](../../reference/command-plane.md).

**Goal:** Convert the now-correct ETHOS product semantics into durable mechanism constraints for lifecycle entry, branch-role configuration, command-plane boundaries, and binding classifications.

**Architecture:** Keep all product behavior inside `packages/ethos-*` and keep repo-local skills, plans, and host projections as workflow projections. Use ETHOS Work Lane commands for mutation isolation and closeout; do not introduce raw Git worktree lifecycle as a product entrypoint. Strengthen tests around existing contracts instead of adding a second command plane or a provider-specific ontology.

**Tech Stack:** Python 3.12, pytest, Ruff, JSON Schema, OpenSpec CLI, ETHOS command JSON, Git worktrees through ETHOS lane commands.

---

## File Structure

- `docs/superpowers/plans/2026-07-01-ethos-mechanism-hardening.md`: tracked execution plan for this batch.
- `tests/unit/test_workspace_lanes.py`: Work Lane lifecycle and role-policy regression tests.
- `tests/unit/test_coupling_governance.py`: binding taxonomy and product/tool/profile boundary regression tests.
- `tests/unit/test_command_registry_depth.py`: public command plane and OpenSpec command boundary regression tests.
- `tests/architecture/test_product_boundaries.py`: product-surface architecture regression tests.
- `docs/architecture/runner-and-mutation.md`: canonical lifecycle mechanism wording if tests expose a documentation gap.
- `docs/governance/product-design-contract.md`: canonical product boundary wording if tests expose a documentation gap.
- `docs/reference/command-plane.md`: command-plane wording if tests expose a command-boundary gap.

## Task 1: Plan And Lane Admission

**Files:**
- Create: `docs/superpowers/plans/2026-07-01-ethos-mechanism-hardening.md`

- [x] **Step 1: Confirm isolated ETHOS lane**

Run:

```bash
uv run --package ethos ethos status --json | jq '{state,role:.data.role,dirty:.data.dirty,closeout_support:.data.closeout_support}'
```

Expected: `role` is `work_lane`, `dirty` is `false`, and `closeout_support.supported` is `true`.

- [x] **Step 2: Admit planned write paths**

Run:

```bash
uv run --package ethos ethos lane prewrite docs/superpowers/plans/2026-07-01-ethos-mechanism-hardening.md tests/unit/test_workspace_lanes.py tests/unit/test_coupling_governance.py tests/unit/test_command_registry_depth.py tests/architecture/test_product_boundaries.py docs/architecture/runner-and-mutation.md docs/governance/product-design-contract.md docs/reference/command-plane.md --require-editor-root --editor-root /Users/yheng/projects/ethos-work-ethos-mechanism-hardening --json
```

Expected: `ok=true`, `state=admitted`, and `blocked_paths=[]`.

## Task 2: Lifecycle Entry Mechanism

**Files:**
- Modify: `tests/unit/test_coupling_governance.py`
- Modify if RED requires it: `packages/ethos-repository/src/ethos_repository/coupling.py`
- Modify if documentation is stale: `docs/architecture/runner-and-mutation.md`

- [x] **Step 1: Write failing lifecycle binding test**

Add a test asserting that the binding registry classifies `ethos lane start`, `ethos land`, and `ethos lane retire-landed` as the required lifecycle contract, and that raw `git worktree add` is recorded only as forbidden workflow state, not as a command affordance.

- [x] **Step 2: Verify RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_coupling_governance.py::test_work_lane_lifecycle_binding_excludes_raw_git_worktree_entrypoint -q
```

Expected: fail until the registry or docs expose the exact mechanism contract.

- [x] **Step 3: Implement minimal GREEN**

If the current registry is already correct, keep the test as the mechanism guard. If it fails, update only `packages/ethos-repository/src/ethos_repository/coupling.py` so `work_lane_lifecycle_command_contract` contains ETHOS lifecycle commands and `forbidden_workflow_state=["raw_git_worktree_add"]`.

- [x] **Step 4: Verify GREEN**

Run the same pytest command. Expected: pass.

## Task 3: Configured Branch Roles

**Files:**
- Modify: `tests/unit/test_workspace_lanes.py`
- Modify if RED requires it: `packages/ethos-contracts/src/ethos_contracts/branch_roles.py`
- Modify if RED requires it: `packages/ethos-adapters/src/ethos_adapters/status.py`

- [x] **Step 1: Write failing configured-role test**

Add a test using a non-default policy:

```toml
[branch_roles]
release_branch = "release"
accepted_branch = "integration"
candidate_branch = "stage/integration"
work_branch_prefix = "lane/"
submit_branch_prefix = "review/"
```

Assert semantic order is `release_root`, `accepted_root`, `candidate`, `work_lane`, `submit_lane`, and each branch is classified from the configured values.

- [x] **Step 2: Verify RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_workspace_lanes.py::test_branch_role_policy_semantic_order_uses_configured_roles_without_hardcoded_names -q
```

Expected: fail if hard-coded defaults leak into role order or classification.

- [x] **Step 3: Implement minimal GREEN**

If current behavior already satisfies the contract, keep the test as a guard. If not, update branch role policy loading/classification only.

- [x] **Step 4: Verify GREEN**

Run the same pytest command. Expected: pass.

## Task 4: OpenSpec And Command Plane Boundary

**Files:**
- Modify: `tests/unit/test_command_registry_depth.py`
- Modify if RED requires it: `packages/ethos-repository/src/ethos_repository/command_registry.py`
- Modify if documentation is stale: `docs/reference/command-plane.md`

- [x] **Step 1: Write failing command-boundary test**

Add a test asserting that public workflow commands are exactly `ethos status`, `ethos plan`, `ethos prove`, `ethos land`, and `ethos publish`; `ethos openspec` is maintainer reference only; raw `openspec validate --all --strict --json` appears as an official governance gate, not a product command plane replacement.

- [x] **Step 2: Verify RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_command_registry_depth.py::test_openspec_is_governance_dependency_not_second_public_command_plane -q
```

Expected: fail if command registry exposes OpenSpec as public workflow.

- [x] **Step 3: Implement minimal GREEN**

If current behavior already satisfies the contract, keep the test as a guard. If not, update command registry classification only.

- [x] **Step 4: Verify GREEN**

Run the same pytest command. Expected: pass.

## Task 5: Product Binding Boundary Regression

**Files:**
- Modify: `tests/unit/test_coupling_governance.py`
- Modify: `tests/architecture/test_product_boundaries.py`
- Modify if RED requires it: `packages/ethos-repository/src/ethos_repository/coupling.py`

- [x] **Step 1: Write failing binding-boundary tests**

Add tests that assert Git remains `product_semantic_hard_binding`; OpenSpec remains `mandatory_governance_dependency`; `uv`, `pytest`, `Ruff`, and hatchling remain `product_toolchain_binding`; GitLab, MCP, ACP, and npm launcher remain `profile_or_adapter_binding`; legacy evidence remains `legacy_evidence`; fixtures remain `test_fixture`.

- [x] **Step 2: Verify RED**

Run:

```bash
uv run --group dev pytest tests/unit/test_coupling_governance.py::test_binding_registry_keeps_each_binding_in_its_mechanism_layer tests/architecture/test_product_boundaries.py::test_current_product_surfaces_do_not_use_host_projection_labels -q
```

Expected: fail until all bindings and product surfaces are guarded.

- [x] **Step 3: Implement minimal GREEN**

If the registry already satisfies the layer assertions, keep tests as guards. If product surfaces contain host projection labels, update only current product docs, not historical evidence/archive.

- [x] **Step 4: Verify GREEN**

Run the same pytest command. Expected: pass.

## Task 6: Full Verification And Closeout

**Files:**
- No new files beyond task changes.

- [x] **Step 1: Run changed route**

```bash
uv run --package ethos ethos playbooks route --changed --json
```

Expected: selected skill includes `ethos-repository-governance`; unmatched paths are empty.

- [x] **Step 2: Run focused and broad tests**

```bash
uv run --group dev pytest tests/unit/test_workspace_lanes.py tests/unit/test_coupling_governance.py tests/unit/test_command_registry_depth.py tests/architecture/test_product_boundaries.py -q
uv run --group dev pytest tests/unit tests/architecture -q
```

Expected: all pass.

- [x] **Step 3: Run product and governance gates**

```bash
uv run --group dev ruff check .
uv run openspec validate --all --strict --json
uv run --package ethos ethos playbooks check --mode v2-strict --json
uv run --package ethos ethos report --json
uv run --package ethos ethos prove --full --execute --expect-head "$(git rev-parse HEAD)" --json
```

Expected: all pass; report remains `score=15`, `governance_gap_count=0`, and `parity_pending_count=0`.

- [x] **Step 4: Commit and closeout**

```bash
git add docs/superpowers/plans/2026-07-01-ethos-mechanism-hardening.md packages/ethos-repository/src/ethos_repository/command_registry.py packages/ethos-repository/src/ethos_repository/coupling.py tests/unit/test_workspace_lanes.py tests/unit/test_coupling_governance.py tests/unit/test_command_registry_depth.py tests/architecture/test_product_boundaries.py
git commit -m "Harden ETHOS mechanism boundaries"
uv run --package ethos ethos land --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
uv run --package ethos ethos land --closeout --apply --authorize --expect-head "$(git -C /Users/yheng/projects/ethos rev-parse HEAD)" --root /Users/yheng/projects/ethos --json
uv run --package ethos ethos lane retire-landed --branch work/ethos-mechanism-hardening --apply --json
```

Expected: local `dev` and `candidate/dev` end at the same commit. No remote command is run.

## Self-Review

- Spec coverage: lifecycle entry, role-policy configuration, OpenSpec boundary, binding layer taxonomy, product host-neutrality, proof, land, local ff, and lane retirement are covered.
- Placeholder scan: no placeholders remain; every task has exact files and commands.
- Type consistency: tests target existing ETHOS concepts: `binding_registry`, `BranchRolePolicy`, command registry, product surfaces, and ETHOS proof/report JSON.
