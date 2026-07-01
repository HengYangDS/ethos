---
subject: ethos:asset-quality-kernel-plan
role: plan
state: active
relations:
  change: ethos-asset-quality-kernel
---

# Asset Quality Kernel Implementation Plan

Status: active.

Purpose: record the implementation plan used to promote quality and proof
policy into a first-class ETHOS product capability.

See also: [Documentation Index](../../index.md),
[Command Plane](../../reference/command-plane.md), and
[Glossary](../../reference/glossary.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make quality, determinism, proof classification, and self-evolution first-class ETHOS product capabilities instead of incidental repository lifecycle checks.

**Architecture:** Add `ethos-quality` as a focused semantic package for asset policy, gate descriptors, proof lattice, documentation quality profile, and adopter-profile boundaries. Keep `ethos-repository` responsible for repository lifecycle orchestration only, keep `ethos-contracts` provider-neutral, and expose the new capability through thin `ethos quality ...` CLI reports.

**Tech Stack:** Python 3.12, Hatchling, uv workspace, cyclopts, JSON Schema draft 2020-12, pytest, Ruff, official OpenSpec CLI.

---

### Task 1: Campaign And OpenSpec Contract

**Files:**
- Create: `openspec/changes/ethos-asset-quality-kernel/proposal.md`
- Create: `openspec/changes/ethos-asset-quality-kernel/design.md`
- Create: `openspec/changes/ethos-asset-quality-kernel/tasks.md`
- Create: `openspec/changes/ethos-asset-quality-kernel/specs/ethos-quality/spec.md`
- Create: `openspec/specs/ethos-quality/spec.md`
- Create: `openspec/specs/ethos-quality/capability.toml`
- Modify: `tests/architecture/test_product_boundaries.py`

- [x] **Step 1: Write failing OpenSpec/package tests**

Add assertions that `ethos-quality` is a canonical package and OpenSpec spec family.

- [x] **Step 2: Run RED**

Run: `uv run --group dev pytest tests/architecture/test_product_boundaries.py -q`

Expected: FAIL because `ethos-quality` package/spec does not exist.

- [x] **Step 3: Add OpenSpec records**

Write official change records and canonical `ethos-quality` capability files.

- [x] **Step 4: Run GREEN**

Run: `uv run openspec validate --all --strict`

Expected: PASS after records and package ontology are complete.

### Task 2: Quality Package And Contracts

**Files:**
- Create: `packages/ethos-quality/pyproject.toml`
- Create: `packages/ethos-quality/README.md`
- Create: `packages/ethos-quality/src/ethos_quality/__init__.py`
- Create: `packages/ethos-quality/src/ethos_quality/models.py`
- Create: `packages/ethos-quality/src/ethos_quality/profiles.py`
- Create: `packages/ethos-quality/src/ethos_quality/gates.py`
- Create: `packages/ethos-quality/src/ethos_quality/docs_profile.py`
- Create: `packages/ethos-quality/src/ethos_quality/proof_policy.py`
- Modify: `pyproject.toml`
- Modify: `.ethos/workspace.toml`
- Modify: `packages/ethos-contracts/src/ethos_contracts/package_ontology.py`
- Test: `tests/unit/test_quality_kernel.py`

- [x] **Step 1: Write failing import/model tests**

Test that `ethos_quality` has no `__init__.py` re-exports, exposes asset classes through concrete modules, and reports code/docs/config/shell/evidence/proof/release/adopter-profile quality dimensions.

- [x] **Step 2: Run RED**

Run: `uv run --group dev pytest tests/unit/test_quality_kernel.py -q`

Expected: FAIL because `ethos_quality` does not exist.

- [x] **Step 3: Implement focused quality package**

Add dataclasses and pure report builders. Do not import `ethos_repository`, `ethos_adapters`, provider tools, or adopter-specific terms.

- [x] **Step 4: Run GREEN**

Run: `uv run --group dev pytest tests/unit/test_quality_kernel.py tests/architecture/test_product_boundaries.py -q`

Expected: PASS.

### Task 3: Schema And Proof Lattice

**Files:**
- Create: `schemas/ethos/quality-asset.schema.json`
- Create: `schemas/ethos/quality-finding.schema.json`
- Create: `schemas/ethos/quality-gate-plan.schema.json`
- Create: `schemas/ethos/quality-profile.schema.json`
- Create: `schemas/ethos/review-record.schema.json`
- Create: `schemas/ethos/host-capability.schema.json`
- Modify: `schemas/ethos/gate.schema.json`
- Modify: `schemas/ethos/proof-run.schema.json`
- Modify: `packages/ethos-repository/src/ethos_repository/schema_validation.py`
- Modify: `packages/ethos-repository/src/ethos_repository/evidence.py`
- Modify: `packages/ethos-repository/src/ethos_repository/gates.py`
- Test: `tests/unit/test_schema_validation_and_gates.py`
- Test: `tests/unit/test_cli_contracts.py`

- [x] **Step 1: Write failing schema/lattice tests**

Test that gates include asset classes, dimensions, execution mode, evidence class, trust-bearing flag, tool adapter, file-write policy, network policy, and version source. Test that proof runs use the lattice states `planned`, `readiness`, `executed`, `proven`, `blocked`, `accepted-risk`, and `waived_nonblocking`.

- [x] **Step 2: Run RED**

Run: `uv run --group dev pytest tests/unit/test_schema_validation_and_gates.py tests/unit/test_cli_contracts.py -q`

Expected: FAIL because schemas and model fields are missing.

- [x] **Step 3: Implement schemas and model conversion**

Keep command execution adapter-neutral and let `ethos-quality` provide descriptors.

- [x] **Step 4: Run GREEN**

Run: `uv run --group dev pytest tests/unit/test_schema_validation_and_gates.py tests/unit/test_cli_contracts.py -q`

Expected: PASS.

### Task 4: CLI UX And Docs Quality Profile

**Files:**
- Modify: `packages/ethos/src/ethos/cli.py`
- Modify: `docs/architecture/package-ontology.md`
- Modify: `docs/reference/command-plane.md`
- Modify: `docs/governance/docs-registry.md`
- Test: `tests/unit/test_cli_contracts.py`
- Test: `tests/unit/test_docs_registry.py`
- Test: `tests/unit/test_command_registry_depth.py`

- [x] **Step 1: Write failing CLI/docs tests**

Test `ethos quality asset-policy --json`, `ethos quality docs --json`, `ethos quality proof-policy --json`, and `ethos quality tool-profiles --json`. Test documentation profile reports front matter, purpose/status/see-also, glossary, links, anchors, and command examples as separate mechanical dimensions.

- [x] **Step 2: Run RED**

Run: `uv run --group dev pytest tests/unit/test_cli_contracts.py tests/unit/test_docs_registry.py tests/unit/test_command_registry_depth.py -q`

Expected: FAIL because the new commands and docs profile do not exist.

- [x] **Step 3: Implement thin CLI composition**

CLI only renders reports from `ethos_quality` and existing repository registry modules.

- [x] **Step 4: Run GREEN**

Run: `uv run --group dev pytest tests/unit/test_cli_contracts.py tests/unit/test_docs_registry.py tests/unit/test_command_registry_depth.py -q`

Expected: PASS.

### Task 5: Contracts Boundary And Self-Evolution

**Files:**
- Modify: `packages/ethos-contracts/src/ethos_contracts/capability_parity.py`
- Create: `docs/governance/reference-adopter-parity-ledger.md`
- Modify: `docs/governance/capability-parity-ledger.md`
- Modify: `schemas/ethos/evolution-ledger.schema.json`
- Modify: `docs/governance/self-evolution-ledger.toml`
- Modify: `packages/ethos-repository/src/ethos_repository/evolution.py`
- Test: `tests/unit/test_parity_command.py`
- Test: `tests/unit/test_self_evolution_ledger.py`
- Test: `tests/architecture/test_product_boundaries.py`

- [x] **Step 1: Write failing boundary/evolution tests**

Test that product Python code does not hardcode `alphasim` or `dmgr`, including contracts; adopter parity instances live in docs/profile evidence. Test self-evolution hypotheses include owner, transition, proof refs, review refs, decision refs, and retirement conditions.

- [x] **Step 2: Run RED**

Run: `uv run --group dev pytest tests/unit/test_parity_command.py tests/unit/test_self_evolution_ledger.py tests/architecture/test_product_boundaries.py -q`

Expected: FAIL because contracts still contain reference-adopter instance data and the evolution ledger is too thin.

- [x] **Step 3: Move instance data out of provider-neutral contracts**

Keep generic dataclass/schema in `ethos-contracts`; move dmgr/adopter examples to governance docs and CLI report ingestion.

- [x] **Step 4: Run GREEN**

Run: `uv run --group dev pytest tests/unit/test_parity_command.py tests/unit/test_self_evolution_ledger.py tests/architecture/test_product_boundaries.py -q`

Expected: PASS.

### Task 6: Evidence, Claims, Verification, Closeout

**Files:**
- Create: `claims/ethos-asset-quality-kernel.toml`
- Create: `docs/evidence/asset-quality-kernel-2026-07-01.md`
- Modify: `openspec/changes/ethos-asset-quality-kernel/tasks.md`

- [x] **Step 1: Add claim and dated evidence**

Record scope, touched contracts, validation commands, and SHA-256 digest binding.

- [x] **Step 2: Run focused verification**

Run:

```bash
uv run --group dev pytest tests/unit/test_quality_kernel.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_cli_contracts.py tests/unit/test_docs_registry.py tests/unit/test_self_evolution_ledger.py tests/unit/test_parity_command.py tests/architecture/test_product_boundaries.py -q
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality package-ontology --json
uv run --package ethos ethos self audit --mode deep --json
uv run --package ethos ethos report --json
uv run openspec validate --all --strict
uv run --group dev ruff check .
uv build --all-packages
```

Expected: all PASS.

- [x] **Step 3: Commit and closeout**

Commit from `work/asset-quality-kernel`, then use `ethos land --closeout asset-quality-kernel` or the repository-supported equivalent to stage into `candidate/dev`. Do not push remote.
