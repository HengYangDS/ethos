---
subject: ethos:evidence:coupling-contract-hardening
role: evidence
state: active
relations:
  supports: ethos-coupling-governance
---

# Coupling Contract Hardening Evidence - 2026-07-01

This evidence records the local ETHOS coupling-contract-hardening batch.

## Scope

- Added `schemas/ethos/coupling-audit.schema.json` and wired
  `ethos quality schemas --json` to validate a live coupling-audit instance.
- Added a `schema_validation` diagnostic to
  `ethos quality coupling-audit --json` so coupling output is schema-governed
  like workspace status data.
- Expanded `data.binding_registry` from coarse groups into explicit entries for
  Git repository substrate, configured branch roles, OpenSpec workspace,
  official OpenSpec CLI, command JSON and schema protocols, claims/evidence
  digest protocol, ignored SQLite local state, uv workspace orchestration,
  Hatchling, pytest, Ruff, the configured GitLab release profile, MCP/ACP
  protocol adapters, npm launcher distribution adapter, legacy evidence, and
  provider fixtures.
- Added registry self-checks so missing Git product binding, OpenSpec promoted
  into product substrate, non-product entries owning product semantics, and
  host open or checkout presentation fields become required gaps.
- Kept Git as the product-semantic hard binding. Kept OpenSpec as mandatory
  governance, not a product substrate and not a second command plane.
- Kept adapter presentation derived from `worktree_binding`; host open or
  checkout labels remain outside product state.

Remote publication was intentionally out of scope. Existing foreign Work Lanes
were observed through status output but not read, modified, landed, or retired.

## Verification

Commands run from `work/coupling-contract-hardening`:

```bash
uv run --group dev pytest tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py::test_schema_validation_report_covers_all_ethos_schemas tests/unit/test_schema_validation_and_gates.py::test_coupling_audit_payload_validates_binding_registry_contract tests/unit/test_schema_validation_and_gates.py::test_coupling_audit_schema_rejects_ui_projection_fields tests/unit/test_cli_contracts.py::test_quality_coupling_audit_reports_git_native_boundary tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_configured_role_and_binding_contracts -q
uv run --group dev pytest tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_cli_contracts.py tests/architecture/test_product_design_contract.py -q
uv run --group dev pytest -q
uv run --group dev ruff check .
uv build --all-packages
uv run openspec validate --all --strict --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality coupling-audit --json
uv run --package ethos ethos self audit --mode shape --json
uv run --package ethos ethos report --json
uv run --package ethos ethos quality release-policy --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos prove --execute --gate self-audit --gate claims --gate schemas --expect-head "$(git rev-parse HEAD)" --json
```

Observed results:

- RED target set initially failed on missing long-tail binding entries, missing
  registry self-check gaps, missing `coupling-audit.schema.json`, missing
  coupling-audit CLI schema diagnostic, and missing OpenSpec/adapters contract
  wording.
- Focused RED/GREEN target set: `11 passed`.
- Related coupling, schema, CLI, and product-contract set: `95 passed`.
- Full pytest: `271 passed in 67.58s`.
- Ruff: all checks passed.
- Package build: all workspace packages built as sdist and wheel.
- OpenSpec strict validation: `8` specs passed, `0` failed.
- Schema quality: `ok=true`, `schema_count=22`, `required_gaps=[]`, with
  `coupling-audit.schema.json` valid and `coupling-audit-contract` instance
  validation passing.
- Coupling audit: `ok=true`, `required_gaps=[]`, with `schema_validation`
  diagnostic `ok=true` for `coupling-audit.schema.json`.
- Self audit shape mode: `ok=true`, `required_gaps=[]`.
- Report: `ok=true`, score `15/15`, `product_gap_count=0`, and
  `parity_pending_count=0`.
- Release policy: `ok=true`, `required_gaps=[]`.
- Claims quality after claim binding: `ok=true`, `required_gaps=[]`, and
  `ethos-coupling-governance` pointed to this evidence record.
- Proof kernel after claim binding: `ok=true`, `state=proven`, `gate_count=3`,
  and `required_gaps=[]`.
