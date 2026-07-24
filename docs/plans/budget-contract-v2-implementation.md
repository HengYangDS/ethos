---
subject: ethos:quality:budget-contract-v2-implementation
role: plan
state: planned
relations:
  implements: docs/decisions/accepted/DR-0008-metric-domain-budget-contract.md
  governed_by: openspec/changes/archive/2026-07-19-budget-contract-v2-foundation-integration-continuation
---

# Budget Contract v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish Budget Contract v2 as ETHOS's authoritative repository-source budget, preserve per-file ELOC, retire global LOC enforcement without laundering v1 debt, and close the terminal compression program with evidence.

**Architecture:** A typed carrier inventory feeds versioned native metric adapters and produces immutable metric vectors. Pure policy reducers apply non-compensating repository and changed-scope rules; v1 and v2 run through shadow and dual-control states before v2 cutover. Evidence, derived projections, tests, repository source, and agent runtime budgets remain separate domains.

**Tech Stack:** Python 3.14, Pydantic/frozen dataclasses, Git plumbing, stdlib `tokenize`/`ast`/`tomllib`/`configparser`, PyYAML, parse-only Jinja2 source-budget measurement with no adoption rendering, repository-owned parser adapters, TOML policy, JSON Schema, pytest, Ruff, OpenSpec 1.6, ETHOS Work Lane lifecycle.

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
- Archived carrier: `openspec/changes/archive/2026-07-19-budget-contract-v2-foundation/**`
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
- Create: `system/policies/source-budget-carriers.toml`
- Create: `system/policies/source-budget-metrics.toml`
- Create: `system/schemas/kernel/source-budget-carriers.schema.json`
- Create: `system/schemas/kernel/source-budget-metrics.schema.json`
- Create: `tests/unit/kernel/test_source_budget_carriers_contract.py`
- Create: `tests/unit/kernel/test_source_budget_metrics_contract.py`
- Create: `tests/unit/adapters/repo/source_budget/test_carriers.py`
- Modify: `tests/unit/governance/validation/test_schemas.py`
- Preserve unchanged: `packages/ethos-core/src/ethos_core/contracts/source_budget/__init__.py`
- Preserve unchanged: `packages/ethos/src/ethos/adapters/repo/source_budget/__init__.py`
- Preserve unchanged: `packages/ethos/src/ethos/adapters/repo/source_budget/core.py`

**Interfaces:**

- Consumes: one Git-present tagged path observation and the metric-domain
  decision from Task 1.
- Produces: `PresentWorktreePathsLoad`, `CarrierManifest`, `CarrierIdentity`,
  `CarrierMatch`, `CarrierInventory`, `MetricContractSet`, and canonical
  manifest/inventory/metric-contract-set digests.
- Boundary: this task classifies paths and contract identity but does not open
  carrier bytes, invoke parsers, count metrics, or change v1 authority.

- [x] **Step 1: Write adversarial contract tests.**

Cover exact-one classification, unknown fields, duplicate rules, unsupported
extensions, the enumerated canonical segment matcher dialect, surrogate and
non-canonical paths, synthetic-label collision, declaration-order determinism,
Git failure, strict NUL framing, tag/stage consistency, empty inventory,
symlink/gitlink modes, symlink ancestors, stable inventory order, exact
path/id/gap tokens, full-identity digest binding, and digest forgery.

- [x] **Step 2: Run RED and verify the intended missing API/invariant failures.**

The original RED established absent contract modules. Post-review RED runs then
proved the missing typed inventory API and the exact matcher/inventory
invariants before remediation.

- [x] **Step 3: Implement strict contracts and typed repository loaders.**

Required API:

```python
def load_carrier_manifest(root: Path) -> CarrierManifestLoad: ...
def load_present_worktree_paths(root: Path) -> PresentWorktreePathsLoad: ...
def classify_carrier(relative: str, manifest: CarrierManifest) -> CarrierMatch: ...
def classify_carriers(
    paths: Iterable[str],
    manifest: CarrierManifest,
) -> CarrierInventory: ...
def load_metric_contracts(root: Path) -> MetricContractSetLoad: ...
def resolve_metric_contracts(
    identity: CarrierIdentity,
    contracts: MetricContractSet,
) -> tuple[MetricContract, ...]: ...
```

The three loaders return explicit fail-closed envelopes. Git-present inventory
uses one strictly NUL-framed tagged `git ls-files` observation, validates
tag/stage consistency, rejects unsupported tracked modes before worktree
materialization, checks every path ancestor with `lstat`, and never exposes a
clean partial path set. The matcher dialect rejects the enumerated
non-canonical syntax and redundancy set without claiming arbitrary glob
equivalence. `CarrierMatch` carries explicit `path_state` instead of
inferring synthetic status from pathname text and validates path/ID/gap
invariants; `CarrierInventory` orders unique `(relative_path, path_state)` keys,
binds full identity, and recomputes its digest during validation. The carrier
manifest remains independently owned
by `system/policies/source-budget-carriers.toml`; Task 2 does not reuse the v1
format-selection taxonomy and does not modify the v1 adapter.

- [x] **Step 4: Run focused and owner quality gates to GREEN.**

Run the focused carrier, metric, adapter, and schema tests; Python
lint/format/ratchet; config lint; JSON Schema checks; module-layout; and the v1
source-budget advisory. Do not expand any ratchet baseline.

- [x] **Step 5: Complete the bounded claim, Chronicle, independent review,
strict lifecycle proof, and official archive inputs; commit the final T2
carrier.**

Use a HEAD-bound pre-archive proof only after tracked governance and parity
evidence are committed. Archive, archive parity/proof, candidate land,
accepted-root closeout, local publication, and owned-Lane retirement are
subsequent separately evidenced transitions.

### Task 3: Native Measurement Adapters And Adversarial Corpus

**Files:**

- Create: packages/ethos-core/src/ethos_core/contracts/source_budget/measurements.py
- Create: `packages/ethos-core/src/ethos_core/contracts/source_budget/measurement/__init__.py`
- Create: packages/ethos-core/src/ethos_core/contracts/source_budget/measurement/admission.py
- Create: packages/ethos-core/src/ethos_core/contracts/source_budget/measurement/canonical.py
- Modify: packages/ethos-core/src/ethos_core/contracts/source_budget/metrics.py
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/__init__.py`
- Create: packages/ethos/src/ethos/adapters/repo/source_budget/measurement/core.py
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/__init__.py`
- Create: packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/core.py
- Create: packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/_structured.py
- Create: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/shell/__init__.py`
- Create: packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/shell/core.py
- Create: packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/shell/grammar.py
- Create: tests/unit/kernel/source_budget_measurement_support.py
- Create: tests/unit/kernel/test_source_budget_measurements_contract.py
- Create: tests/unit/kernel/test_source_budget_measurements_integrity.py
- Create: tests/unit/adapters/repo/source_budget/test_measurement.py
- Create: tests/unit/adapters/repo/source_budget/test_measurement_orchestration.py
- Create: tests/unit/adapters/repo/source_budget/test_measurement_shell_regressions.py
- Create: tests/unit/adapters/repo/source_budget/test_measurement_yaml_regressions.py
- Create: tests/fixtures/source-budget-v2/cases.toml
- Modify: docs/plans/budget-contract-v2-design.md
- Modify: docs/plans/global-declarative-compression-program.md
- Modify: .config/checks/deptry/policy.toml
- Create: openspec/changes/budget-contract-v2-native-measurement/specs/repository-governance/spec.md
- Create: openspec/changes/budget-contract-v2-native-measurement/specs/quality/spec.md
- Modify via official archive: openspec/specs/quality/spec.md
- Modify via official archive: openspec/specs/repository-governance/spec.md
- Modify: packages/ethos-core/src/ethos_core/contracts/source_budget/carriers.py
- Modify: system/policies/source-budget-carriers.toml
- Modify: system/schemas/kernel/source-budget-carriers.schema.json
- Modify: system/policies/source-budget-metrics.toml
- Modify: system/schemas/kernel/source-budget-metrics.schema.json
- Modify: packages/ethos/pyproject.toml
- Modify: tests/architecture/test_dependency_prose_schema_gates.py
- Modify: tools/ci/scripts/run-dependency-hygiene.sh
- Modify: packages/ethos/src/ethos/surface/cli/_base.py
- Create: tests/unit/cli/test_adoption_root_resolution.py
- Modify: uv.lock

**Interfaces:**

- Consumes: Task 2 carrier inventory, carrier matches, metric profiles, and metric contracts.
- Produces measure_native(content, contracts) -> NativeMeasurementLoad,
  measure_carrier(root, match, contracts) -> CarrierMeasurementLoad, and
  measure_snapshot(root, inventory, contracts) -> MeasurementSnapshotLoad.
- Binds exact raw content separately from normalized/vector identity; T3 is
  descriptor-bound per file, while immutable Git blob/HEAD identity and
  cross-file replay remain Task 4.

- [x] **Step 1: Add contract and adapter RED tests for strict self-verifying models, XOR envelopes, canonical-runtime and provider-signature mismatch, conformance fingerprint drift, Python statement-packing non-reduction and identifier/literal changes, structured pretty/minified equivalence, duplicate/non-finite/unsafe data, Jinja dynamic units/bytes/static separation and non-finite numeric rejection, Shell v4 heredoc/function/case/Bash-Zsh constructs, contextual nested substitution closers and recursion-exhaustion classification, YAML tag-canonical keys, C4 grammar, invalid UTF-8, BOM/CRLF, resource exhaustion, symlink/object drift, reviewed exclusions, reversed order, domain movement, digest forgery, and whole-result rejection.**
- [x] **Step 2: Run the focused tests and retain the intended missing-contract/provider/orchestration failures before adding production owners.**
- [x] **Step 3: Implement canonical CPython 3.14 runtime admission, repository-owned provider descriptors, conformance self-test and exact dispatch, strict native parsers, descriptor-relative no-follow reads with cleanup even when descriptor registration exhausts memory, stable non-sensitive public resource gaps, pre/post object-state checks, classified-only measurement, exclusion-aware inventory binding, deterministic non-compensating aggregation, and fail-closed JSON adoption handling for missing or non-directory explicit roots.**
- [x] **Step 4: Replace ambiguous or inaccurate provider versions with canonical-runtime identities, derive grammar digests and reviewed conformance fingerprints from canonical descriptors, bind Shell v4, Jinja v3, and YAML v2 atomically, bound PyYAML to the admitted major, and run the complete inventory in forward and reversed order. The two runs must bind identical manifest, inventory, contract-set, provider-coverage, and stable-gap identities; when the intentional YAML graph gap is present, snapshot/vector outputs and their digests remain absent rather than being manufactured.**

  The fresh exact-HEAD run at 003623e2cf00057f5504cc0e096caacc5bb7a266
  classified 2,883 paths: 2,880 classified carriers and 3 reviewed exclusions.
  Forward and reverse runs bound identical manifest
  520edd6df6c9e5347f0385fcf8d33d0efb2cb670a28a6257b296044ccdc74971,
  inventory e7bea9d4e967aa244c811234c511c6fc395fea29e61343cae07b3bfa9514b49c,
  and metric-contract-set
  95939bf450efceb8b40b7e19ee5d870fb0d858face2686ffb8fe53259d756cef
  identities. All provider conformance checks matched. Both directions returned
  only source_budget_native_parse_failed:yaml:.config/ci/templates/hosted/gitlab-ci.yml,
  so snapshot/vector payloads and their digests remained absent as required.

- [x] **Step 5: Complete the pre-transition closeout as a distinct state: current-head focused/integration/regression and owner gates, the one-binding observation, exact promotion targets, independent review, claim/Chronicle, generic parity, the final active-carrier recording commit, and then default and full exact-HEAD proof of that commit.**
- [x] **Step 6: Complete official OpenSpec archive and canonical contracts/quality/repository-governance spec fusion as a separate committed state; do not treat archive as archive-HEAD proof or integration.**
- [ ] **Step 7: Complete post-archive parity, default and full archive-HEAD proof, candidate land, accepted-root closeout, local publication-readiness evaluation, and owned successor-Lane retirement as separately evidenced transitions; do not claim remote publication or hosted CI.**

### Prerequisite C1: Versioned Static Hybrid Carrier Execution

**Files:**

- Modify: `packages/ethos-core/src/ethos_core/contracts/source_budget/metrics.py`
- Create: `packages/ethos-core/src/ethos_core/contracts/source_budget/measurement/execution.py`
- Create: `packages/ethos-core/src/ethos_core/contracts/source_budget/measurement/worker/`
- Modify: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/core.py`
- Refactor: `packages/ethos/src/ethos/adapters/repo/source_budget/measurement/native/`
- Modify: `system/policies/source-budget-metrics.toml`
- Modify: `system/schemas/kernel/source-budget-metrics.schema.json`
- Create: `system/schemas/kernel/source-budget-worker-protocol.schema.json`
- Modify/Create: focused kernel, adapter, architecture, adversarial, and platform tests

**Interfaces:**

- Consumes: Task 3 classification, exact provider signatures, descriptor-bound
  reads, native measurement, and fail-closed Loads.
- Produces: MetricContract wire version 4 with static provider routing, fixed
  carrier ceilings, execution-contract id/digest, a strict worker protocol,
  bounded linear reads, one-shot complex-parser isolation, and no partial
  measurement.
- Static bounded parser ids: `utf8-footprint`, `utf8-control`, and
  `diagram-contract`, all under
  `ethos-source-budget-execution:bounded-in-process-v1`.
- Static isolated parser ids: `python-tokenize`, `json-stdlib`, `tomllib`,
  `pyyaml-safe`, `configparser`, `jinja2`, and `shell-lexical`, all under
  `ethos-source-budget-execution:isolated-worker-v1`.
- Boundary: v1 remains authoritative and v2 inactive. C1 does not implement Git
  replay, fix YAML, add v2 policy/debt/gates, or change v1 allowance, debt,
  terminal targets, global LOC, or per-file ELOC.

- [x] **Step 1: Record the bounded-only v3 precursor and independent security rejection; discard only the uncommitted reader/native GREEN, retain committed v3 contracts/tests as explicit migration input, and amend governance to v4 static hybrid execution.**
- [x] **Step 2: Write and verify eight diagnostic MetricContract v4 RED nodes: bounded positive, isolated positive, complete-v3 rejection, helper four-tuple, parser-global mode/id/digest drift, identity propagation with unchanged measurement vector, schema requirements, and exact repository policy mapping.**
- [x] **Step 3: Implement the pure-kernel execution owner, descriptor-only protocol/resource owners, v4 contracts/helper, provider descriptor v2, generated schemas, 28 policy atoms, and owner-computed digest goldens atomically. The helper returns `(mode, ceiling, id, digest)` and current policy has four parameterized execution digests.**
- [x] **Step 4: Write and verify pure worker-protocol RED for typed request/result XOR, exact gap allowlist, canonical five-digest binding, parent replay, length framing, canonical JSON, truncation, duplicates, overlimits, and trailing data.**
- [x] **Step 5: Implement the pure kernel protocol and frame codecs without subprocess behavior.**
- [x] **Step 6: Write router/import-boundary RED and split bounded provider identity/engine from isolated provider engine; prove no isolated failure can call an in-process fallback.**
- [x] **Step 7: Write supervisor/backend RED for private launch, resource setup before import, bounded nonblocking pipes, CPU/RSS/wall/FD/process/output/protocol failures, TERM/KILL/reap, descendants, and Linux/Darwin capability paths.**
- [x] **Step 8: Implement one-carrier/one-process worker bootstrap, POSIX supervisor, Linux/Darwin telemetry, stable redacted gaps, and strict parent result reconstruction.**
- [x] **Step 9: Implement the common single-read parent boundary for both modes and direct native recheck; prove limit-minus-one/exact-limit success, limit-plus-one rejection, pre-spawn safety, drift semantics, and all-or-nothing snapshots.**
- [x] **Step 10: Complete the C1 pre-transition closeout: exact-ceiling and deep/wide provider acceptance, performance and current/immutable inventory evidence, focused 100 percent coverage, every owner gate, independent security/contract/simplicity/platform review, exact promotion targets, semantic Claim binding, parity, exact-HEAD default/full proof, and the same-SHA Linux CPython 3.14 receipt. If hybrid is rejected, keep C1 open and do not raise a ceiling.**

  C1 pre-transition closeout completed at final pre-archive HEAD
  `4071bad853608ec60a43f987363f99f7ba9aaf6e`. The focused selection passed 739
  tests with 4,007 of 4,007 statements and 1,202 of 1,202 branches; the complete
  owner suite passed 3,446 tests with 25,595 of 25,595 lines and 6,896 of 6,896
  branches. Darwin and Linux Python 3.14 checks passed over all 31 changed
  package-source paths, and the zero-tolerance package owner gate remained
  clean. Exact-HEAD default and full proof reached proven state with 21 and 30
  gates. A local Linux arm64 CPython 3.14 receipt ran 21 tests with zero failures
  against the same HEAD and tree. V1 authority, debt, terminal targets, global
  LOC, and per-file ELOC were unchanged; v2 remained inactive.

Post-archive parity/proof, candidate land, accepted-root closeout, local
publication readiness, and owned-Lane retirement remain mandatory separate
transitions. Remote publication and hosted CI are not claimed by C1.

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

- Consumes: Task 3 measurement capability and fail-closed Loads plus the
  accepted C1 resource boundary. It does not assume that the current worktree
  already yields a successful snapshot.
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
- [ ] **Step 3: Run `tools/ci/scripts/run-ethos-lane.sh prove --execute --expect-head "$(git rev-parse HEAD)" --json` and `tools/ci/scripts/run-ethos-lane.sh prove --execute --full --expect-head "$(git rev-parse HEAD)" --json`; require both clean for terminal completion.**
- [ ] **Step 4: Archive through official OpenSpec, update carrier/digests, prove the archive HEAD, land to candidate, then perform audited accepted-root closeout.**
- [ ] **Step 5: Evaluate local `publish --json`, retire the owned landed Lane, and report remote publication and hosted CI separately.**
