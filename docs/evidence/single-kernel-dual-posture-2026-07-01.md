---
subject: ethos:evidence:single-kernel-dual-posture
role: evidence
state: active
relations:
  supports: ethos-single-kernel-dual-posture
---

# Single-Kernel Dual-Posture Evidence - 2026-07-01

This evidence records the local ETHOS batch that makes self-governance and
adopter governance share one product contract.

## Scope

- Added a provider-neutral `governance_context` contract in `ethos-contracts`.
- Exposed the same context from product self-audit and adopter audit payloads.
- Projected `governance_context` through `ethos report --json`.
- Renamed active report gap layers to posture-neutral names:
  `governance_audit`, `capability_parity`, and `playbook_projection`.
- Changed generated adopter rules and CI projections to use `ethos report` and
  `ethos prove` as the default governance and proof entrypoints.
- Kept `ethos self audit` as a self-hosting depth command, not a separate
  product command plane.
- Updated canonical docs and OpenSpec specs to define the single-kernel
  dual-posture model, with `product_self` and `adopter_repository` as postures
  of one repository governance model.

Remote publication was intentionally out of scope. Existing foreign Work Lanes
were observed through status output but not modified, landed, or retired.

## Verification

Commands run from `work/single-kernel-dual-posture`:

```bash
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_uses_adopter_scorecard_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_scorecard_is_derived_from_governance_checks
uv run --group dev pytest -q tests/unit/test_adopt_apply_sample.py::test_adopt_rules_use_single_kernel_governance_entrypoints tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_single_kernel_dual_posture
uv run --group dev pytest -q tests/architecture/test_product_design_contract.py tests/unit/test_self_governance_depth.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_adopt_apply_sample.py
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/unit/test_cli_contracts.py::test_prove_uses_adopter_audit_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_uses_adopter_scorecard_for_non_product_repo tests/unit/test_cli_contracts.py::test_report_scorecard_is_derived_from_governance_checks tests/unit/test_cli_contracts.py::test_prove_returns_evidence_and_provenance
uv run openspec validate --all --strict --json
uv run --package ethos ethos self audit --mode shape --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos report --json
uv run --group dev pytest -q
uv run --group dev ruff check .
uv build --all-packages
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos quality release-policy --json
uv run --package ethos ethos prove --execute --gate self-audit --gate claims --gate schemas --expect-head "$(git rev-parse HEAD)" --json
uv run --package ethos ethos campaign closeout --adopter alphasim-dmgr --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --json
```

Observed results:

- RED CLI contract tests failed with missing `governance_context` and
  `governance_gap_count` keys.
- RED adopter scaffold and product design tests failed with missing
  single-kernel dual-posture rules and docs.
- Focused CLI contract GREEN run: `4 passed`.
- Focused adopter scaffold and design GREEN run: `2 passed`.
- Architecture, self-governance, schema, and adopter scaffold run:
  `34 passed`.
- Focused CLI proof/report run: `5 passed`.
- OpenSpec strict validation: `9` items passed, `0` failed. The base included
  one active OpenSpec change from another Work Lane; this batch did not modify
  that change.
- Self audit shape mode: `ok=true`, `required_gaps=[]`, and
  `governance_context.posture=product_self`.
- Schema quality: `ok=true`, `schema_count=28`, `required_gaps=[]`.
- Report: `ok=true`, score `15/15`, `governance_gap_count=0`, and
  `parity_pending_count=0`.
- Clean-worktree full pytest after commit: `315 passed in 65.82s`.
- Full Ruff after commit: all checks passed.
- Package build after commit: all workspace packages built as sdist and wheel.
- Claim quality after commit: `ok=true`, `required_gaps=[]`, and
  `ethos-single-kernel-dual-posture` matched this evidence digest.
- Release policy after commit: `ok=true`, `required_gaps=[]`.
- Proof kernel after commit: `ok=true`, `state=proven`, `gate_count=3`,
  `required_gaps=[]`, and the expected HEAD matched the command's current HEAD.
- Campaign closeout after commit: `ok=true`, `state=local_ready`,
  `remote_state=deferred`, local closeout supported
  `work/single-kernel-dual-posture -> candidate/dev`, `claim_binding=bound`,
  and `required_gaps=[]`.
