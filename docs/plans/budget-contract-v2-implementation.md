---
subject: ethos:quality:budget-contract-v2-implementation
role: plan
state: planned
relations:
  implements: docs/decisions/accepted/DR-0008-metric-domain-budget-contract.md
  governed_by: openspec/changes/budget-contract-v2-foundation-integration-continuation-20260719
---

# Budget Contract v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish Budget Contract v2 as ETHOS's authoritative repository-source budget, preserve per-file ELOC, retire global LOC enforcement without laundering v1 debt, and close the terminal compression program with evidence.

**Architecture:** A typed carrier inventory feeds versioned native metric adapters and produces immutable metric vectors. Pure policy reducers apply non-compensating repository and changed-scope rules; v1 and v2 run through shadow and dual-control states before v2 cutover. Evidence, derived projections, tests, repository source, and agent runtime budgets remain separate domains.

**Tech Stack:** Python 3.14, Pydantic/frozen dataclasses, Git plumbing, stdlib `tokenize`/`ast`/`tomllib`/`configparser`, PyYAML, Jinja2, repository-owned parser adapters, TOML policy, JSON Schema, pytest, Ruff, OpenSpec 1.6, ETHOS Work Lane lifecycle.

## Global Constraints

- The immutable v1 baseline is `2dab77f169eceb2d45f917358c2a7487e7ac8db6`; do not reset it.
- Do not raise v1 allowance, maximum debt, or terminal targets and do not extend any expiry.
- Do not convert LOC to another metric with an average coefficient.
- Hard coordinates combine with logical AND; no cross-coordinate compensation is permitted.
- Per-file ELOC remains a hard readability ceiling after global v1 LOC retirement.
- LLM/BPE tokens are confined to Agent runtime budgets and never enter repository source truth.
- Every production behavior change follows RED, verified RED, minimal GREEN, verified GREEN, refactor.
- Use `tools/ci/scripts/run-ethos-lane.sh`; do not use a bare `ethos` command from a linked Work Lane.
- Every tracked write requires current holder-bound `ethos lane prewrite` admission.
- Each OpenSpec Change is archived and proven before land; candidate/accepted closeout and remote/hosted claims remain distinct.
- A v1 required gap may disappear only through settlement evidence or an equal-or-stronger named v2 successor obligation.
- Migration completion and terminal compression completion are separate claims.

---

### Task 1: Foundation Decision And Behavior-Preserving Extraction

**Files:**
- Create: `docs/decisions/accepted/DR-0008-metric-domain-budget-contract.md`
- Create ignored raw observation: `build/evidence/quality/source-budget/v1-foundation-snapshot.json`
- Record reviewed digest and summary: `evidence/chronicle/budget-contract-v2-foundation-20260719/2026-07-19.md`
- Create: `packages/ethos/src/ethos/domain/source_budget/__init__.py`
- Create: `packages/ethos/src/ethos/domain/source_budget/core.py`
- Create: `tests/unit/domain/source_budget/__init__.py`
- Create: `tests/unit/domain/source_budget/test_core.py`
- Modify: `docs/decisions/accepted/README.md`
- Modify: `docs/decisions/decision-index.md`
- Modify: `docs/decisions/decision-dependency-map.md`
- Modify: `docs/decisions/decision-code-links.md`
- Modify: `docs/plans/README.md`
- Modify: `packages/ethos/src/ethos/domain/prove.py`
- Modify: `packages/ethos/src/ethos/domain/reporting/scoring.py`
- Modify: `packages/ethos/src/ethos/domain/campaign/closeout.py`
- Modify: `system/commands.toml`
- Modify: `tests/unit/domain/test_prove.py`
- Modify: `tests/unit/kernel/test_command_declaration.py`
- Archived carrier: `openspec/changes/archive/2026-07-19-budget-contract-v2-foundation-20260719/**`
- Modify: `evidence/claims/budget-contract-v2-foundation-20260719.toml`
- Modify: `evidence/chronicle/budget-contract-v2-foundation-20260719/2026-07-19.md`

**Interfaces:**
- Consumes: current-candidate `ethos.domain.prove.source_budget_report` behavior,
  taxonomy, campaign enforcement, and v1 policy.
- Produces: `ethos.domain.source_budget.core.source_budget_report(root: Path) -> dict[str, object]` with byte-for-byte equivalent JSON semantics; accepted DR-0008; reviewed v1 fact summary with an ignored raw-evidence digest.

- [x] **Step 1: Move existing source-budget tests to the new module path before production code exists.**

Keep code-size and workspace validation tests in `tests/unit/domain/test_prove.py`. Move source-budget cases into `tests/unit/domain/source_budget/test_core.py`, importing:

```python
from ethos.domain.source_budget.core import (
    source_budget_carrier_report,
    source_budget_report,
)
```

- [x] **Step 2: Run RED.**

Run:

```bash
tools/ci/scripts/with-python-runtime.sh -- uv run --all-packages --group dev pytest -q \
  tests/unit/domain/source_budget/test_core.py \
  tests/unit/kernel/test_command_declaration.py
```

Expected: failure because `ethos.domain.source_budget.core` and the declared provider do not yet exist.

- [x] **Step 3: Extract the v1 implementation without a compatibility forwarder.**

Move the two public reducers, `source_budget_carrier_report` and
`source_budget_report`, plus their source-budget-only private helpers, from
`ethos.domain.prove` to `ethos.domain.source_budget.core`. Category taxonomy
continues to come from the declarative `source_budget_taxonomy(...)` loader; do
not introduce or describe a static category-constant owner. Update the scorecard
import and declare:

```toml
report_handler = { provider = "ethos.domain.source_budget.core:source_budget_report", state_mode = "advisory_gaps", enforce = true, bind_root = true }
```

Do not leave a re-export in `prove.py`.

- [x] **Step 4: Run GREEN and behavior-equivalence checks.**

Run:

```bash
tools/ci/scripts/with-python-runtime.sh -- uv run --all-packages --group dev pytest -q \
  tests/unit/kernel/test_source_budget_contract.py \
  tests/unit/adapters/repo/test_source_budget.py \
  tests/unit/adapters/test_config.py \
  tests/unit/domain/test_prove.py \
  tests/unit/domain/source_budget/test_core.py \
  tests/unit/domain/reporting/test_advisories.py \
  tests/unit/domain/test_report.py \
  tests/unit/governance/test_evolution_ledger.py \
  tests/unit/kernel/test_command_declaration.py \
  tests/unit/audit/test_modes.py \
  tests/unit/cli/test_report_surface.py \
  tests/unit/lanes/test_projection_rebase_source_budget.py
```

Expected: all selected tests pass; controlled inputs retain the same taxonomy,
policy facts, command state and exit status, campaign binding, debt lifecycle,
and required/advisory-gap semantics. The predecessor 17-gap snapshot remains
historical evidence rather than the successor command's current expectation.

- [x] **Step 5: Complete DR-0008, OpenSpec deltas, snapshot, claim, Chronicle, and commit.**

Run strict OpenSpec validation, claim validation, config lint, Python lint, and
commit with:

```bash
git commit -m "refactor(quality): establish budget contract v2 foundation"
```

### Task 2: Typed Carrier And Metric Contracts

**Files:**
- Create: `packages/ethos-core/src/ethos_core/contracts/source_budget/carriers.py`
- Create: `packages/ethos-core/src/ethos_core/contracts/source_budget/metrics.py`
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/carriers.py`
- Create: `system/policies/source-budget-metrics.toml`
- Create: `system/schemas/kernel/source-budget-carriers.schema.json`
- Create: `system/schemas/kernel/source-budget-metrics.schema.json`
- Create: `tests/unit/kernel/test_source_budget_carriers_contract.py`
- Create: `tests/unit/kernel/test_source_budget_metrics_contract.py`
- Create: `tests/unit/adapters/repo/source_budget/test_carriers.py`
- Modify: `packages/ethos-core/src/ethos_core/contracts/source_budget/__init__.py`
- Modify: `packages/ethos/src/ethos/adapters/repo/source_budget/__init__.py`

**Interfaces:**
- Consumes: Git-present paths and metric-domain decision from Task 1.
- Produces: `CarrierManifest`, `CarrierIdentity`, `CarrierMatch`, `MetricContract`, and deterministic manifest/contract digests.

- [ ] **Step 1: Write contract tests for exact-one classification, unknown fields, duplicate rules, unsupported extensions, and digest determinism.**
- [ ] **Step 2: Run the new tests and verify failures are caused by missing contract modules.**
- [ ] **Step 3: Implement frozen contract models and strict TOML/schema loaders.**

Required API:

```python
def load_carrier_manifest(root: Path) -> CarrierManifestLoad: ...
def classify_carrier(relative: str, manifest: CarrierManifest) -> CarrierMatch: ...
def load_metric_contracts(root: Path) -> MetricContractSet: ...
```

- [ ] **Step 4: Run contract, schema, and adapter tests to GREEN.**
- [ ] **Step 5: Commit with `feat(quality): add typed source budget contracts`.**

### Task 3: Native Measurement Adapters And Adversarial Corpus

**Files:**
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/__init__.py`
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/core.py`
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/python.py`
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/structured.py`
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/template.py`
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/languages.py`
- Create: `tests/unit/adapters/repo/source_budget/test_measurement.py`
- Create: `tests/fixtures/source-budget-v2/manifest.toml`
- Create: `tests/fixtures/source-budget-v2/**`

**Interfaces:**
- Consumes: Task 2 carrier and metric contracts.
- Produces: `measure_carrier(...) -> CarrierMeasurement` and `measure_snapshot(...) -> MeasurementSnapshot`.

- [ ] **Step 1: Add adversarial tests for Python statement packing, JSON pretty/minified equivalence, identifier shortening, giant literals/heredocs, parser failure, invalid UTF-8, and domain movement.**
- [ ] **Step 2: Run the adapter tests and verify missing-provider failures.**
- [ ] **Step 3: Implement native adapters using stdlib/PyYAML/Jinja owners and fail closed on unavailable or invalid parsers.**
- [ ] **Step 4: Run the corpus twice with reversed file order and verify identical vectors and digests.**
- [ ] **Step 5: Commit with `feat(quality): measure source budget vectors`.**

### Task 4: Git Snapshot Replay And v2 Shadow Report

**Files:**
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/snapshots.py`
- Create: `tools/ci/source_budget_replay.py`
- Create: `tools/ci/scripts/run-source-budget-replay.sh`
- Create: `.config/checks/source-budget/history.toml`
- Create: `tests/unit/ci/source_budget/test_replay.py`
- Create: `tests/unit/domain/source_budget/test_shadow_report.py`
- Modify: `packages/ethos/src/ethos/domain/source_budget/core.py`
- Modify: `system/tools.toml`

**Interfaces:**
- Consumes: Task 3 measurement snapshot.
- Produces: `tree_snapshot(root, treeish)`, `worktree_snapshot(root)`, baseline replay evidence, and `v2_shadow` report fields.

- [ ] **Step 1: Write failing tests that recompute the immutable baseline from Git blobs and expose the 282-ELOC v1 semantic drift (105342 -> 105060; JavaScript +1, YAML -282, diagram -1) without rewriting the declaration.**
- [ ] **Step 2: Verify RED against the absent snapshot adapter.**
- [ ] **Step 3: Implement batch Git blob reads and a shadow comparison containing v1, v2, digests, coverage, disagreements, and required gaps.**
- [ ] **Step 4: Run baseline and selected historical replays; verify no unresolved disagreement is classified as clean.**
- [ ] **Step 5: Commit with `feat(quality): add source budget replay and shadow`.**

### Task 5: Vector Policy And Debt v2

**Files:**
- Create: `packages/ethos-core/src/ethos_core/contracts/source_budget/policy_v2.py`
- Create: `packages/ethos/src/ethos/domain/source_budget/verdict.py`
- Create: `tests/unit/domain/source_budget/test_verdict.py`
- Modify: `.ethos/rules.toml`
- Modify: `packages/ethos/src/ethos/adapters/config.py`
- Modify: `system/schemas/kernel/source-budget.schema.json`
- Modify: `tests/unit/adapters/test_config.py`
- Modify: `tests/unit/kernel/test_source_budget_contract.py`

**Interfaces:**
- Consumes: v2 observations and immutable replay evidence.
- Produces: `compile_budget_verdict(observations, policy, today) -> SourceBudgetVerdict`.

- [ ] **Step 1: Write failing reducer tests for logical AND, duplicate coordinates, cross-axis conversion, expiry after wave due date, and expected deletion below allowance.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement strict policy/debt models and pure verdict compilation.**
- [ ] **Step 4: Remeasure each v1 debt record or emit an explicit `unmapped` successor gap; run all reducer/config tests to GREEN.**
- [ ] **Step 5: Commit with `feat(quality): add vector policy and debt v2`.**

### Task 6: Changed-Scope Source Admission And Domain Separation

**Files:**
- Create: `packages/ethos/src/ethos/domain/source_budget/change.py`
- Create: `tests/unit/domain/source_budget/test_change_admission.py`
- Create: `system/schemas/kernel/change-source-budget.schema.json`
- Modify: `system/commands.toml`
- Modify: `system/gates.toml`
- Modify: `packages/ethos/src/ethos/domain/reporting/gaps.py`
- Modify: `openspec/specs/quality/spec.md`

**Interfaces:**
- Consumes: candidate merge base, selected OpenSpec scope, and v2 policy.
- Produces: `source_admission_report(root: Path) -> dict[str, object]` and the default `source-admission` gate.

- [ ] **Step 1: Write failing tests proving zero/net-negative changes are not blocked by inherited debt and that positive coordinates require a Change-owned allocation.**
- [ ] **Step 2: Verify RED and command/gate declaration failures.**
- [ ] **Step 3: Implement merge-base measurement and exact Change-bound allocation matching; keep evidence/derived/test coordinates separate.**
- [ ] **Step 4: Run gate graph, command contract, report, OpenSpec, and focused source-admission tests to GREEN.**
- [ ] **Step 5: Commit with `feat(proof): add changed-scope source admission`.**

### Task 7: Dual Control And Calibration Decision

**Files:**
- Create: `docs/decisions/accepted/DR-0009-budget-v2-calibration-and-v1-supersession.md`
- Create: `tests/unit/domain/source_budget/test_dual_control.py`
- Modify: `docs/decisions/**`
- Modify: `.ethos/rules.toml`
- Modify: `packages/ethos/src/ethos/domain/source_budget/core.py`
- Modify: `openspec/specs/quality/spec.md`

**Interfaces:**
- Consumes: two complete stable shadow integration cycles and debt mapping.
- Produces: accepted calibrated v2 ceilings/targets, `v1_and_v2` mode, cutover and rollback conditions.

- [ ] **Step 1: Add failing tests that require both v1 and v2 during dual mode and block unknown disagreements or metric-contract drift.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement dual-mode reducer and record two candidate integration receipts without changing metric semantics between them.**
- [ ] **Step 4: Accept DR-0009 only after replay, mapping, parity, determinism, and rollback-drill evidence are complete.**
- [ ] **Step 5: Commit with `feat(quality): enable budget v2 dual control`.**

### Task 8: v2 Authority And Global v1 LOC Retirement

**Files:**
- Modify: `.ethos/rules.toml`
- Modify: `packages/ethos/src/ethos/domain/source_budget/core.py`
- Modify: `packages/ethos/src/ethos/domain/source_budget/verdict.py`
- Modify: `system/schemas/kernel/source-budget.schema.json`
- Modify: `docs/plans/global-declarative-compression-program.md`
- Modify: `openspec/specs/quality/spec.md`
- Delete: v1 global LOC-only reducer helpers and tests
- Retain: `packages/ethos-core/src/ethos_core/measure.py` and `code_size_report`

**Interfaces:**
- Consumes: accepted DR-0009 and clean dual-control admission.
- Produces: v2-authoritative repository source budget with one rollback window and no global LOC currency.

- [ ] **Step 1: Write failing tests that reject a v1 global LOC policy in authoritative-v2 mode while preserving per-file code-size ELOC.**
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Switch authority, retain v1 compatibility output only for the declared rollback window, and remove global LOC enforcement.**
- [ ] **Step 4: Run default/full proof graphs, code-size, source-admission, source-budget, parity, and rollback drill.**
- [ ] **Step 5: Commit with `feat(quality): make budget v2 authoritative`.**

### Task 9: Terminal Compression Settlement

**Files:**
- Modify/Delete: exact debt-owned source and test paths identified by Debt v2 mapping
- Modify: `.ethos/rules.toml`
- Modify: `docs/plans/global-declarative-compression-program.md`
- Modify: tracked claim and Chronicle for each settlement Change

**Interfaces:**
- Consumes: authoritative v2 vectors and named expected-deletion obligations.
- Produces: zero active, expired, unmapped, and unclassified debt with every terminal coordinate passing.

- [ ] **Step 1: Select one named debt record and add a failing settlement assertion for its exact coordinate and scope.**
- [ ] **Step 2: Delete or simplify the owned implementation without weakening behavior tests.**
- [ ] **Step 3: Run the named behavior tests and terminal source-budget check.**
- [ ] **Step 4: Repeat one debt record per governed Change until the debt inventory and terminal vector are clean.**
- [ ] **Step 5: Commit each settlement with `refactor(compression): settle <debt-id>`.**

### Task 10: Final Proof, Archive, Land, Closeout, Publish Readiness, And Retirement

**Files:**
- Modify: final active OpenSpec Change tasks/deltas
- Modify: final claim/Chronicle and `evidence/parity/generic-shadow.json`
- Move via official CLI: active Change to dated archive

**Interfaces:**
- Consumes: all prior tasks on a stable HEAD.
- Produces: archived Change, HEAD-bound executed proof, candidate integration, accepted-root closeout, local publication-readiness result, and retired owned Lane.

- [ ] **Step 1: Run focused owner checks, complete test suite, lint/config/schema/quality audit, strict OpenSpec lifecycle, and parity gaps.**
- [ ] **Step 2: Refresh tracked parity evidence when stale, commit it, and rerun checks at the new HEAD.**
- [ ] **Step 3: Run `ethos prove --execute --expect-head <HEAD>` and `ethos prove --full --execute --expect-head <HEAD>`; require both clean for terminal completion.**
- [ ] **Step 4: Archive through official OpenSpec, update carrier/digests, prove the archive HEAD, land to candidate, then perform audited accepted-root closeout.**
- [ ] **Step 5: Evaluate local `publish --json`, retire the owned landed Lane, and report remote publication and hosted CI separately.**
