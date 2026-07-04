---
subject: ethos:evidence:binding-productization
role: evidence
state: active
relations:
  supports: ethos-coupling-governance
---

# Binding Productization Evidence - 2026-07-01

This evidence records the local ETHOS binding-productization batch.

## Scope

- Promoted configured branch-role policy to product JSON through
  `data.role_policy`.
- Ordered configured branch roles as
  `release_root -> accepted_root -> candidate -> work_lane -> submit_lane`.
- Renamed the submit role to `submit_lane` so `submit/*` is modeled as a lane
  role, not an unqualified branch label.
- Kept host open or checkout labels outside product status payloads; adapters
  may project them from `worktree_binding`, but adapter UI text is not product
  state.
- Added `data.binding_registry` to coupling audit so Git substrate, branch role
  policy, OpenSpec, native protocols, self-hosting tools, host profiles,
  assistant protocol adapters, legacy evidence, and fixtures are classified
  explicitly.
- Kept Git as the product-semantic hard binding and OpenSpec as mandatory
  governance, not a product substrate or second command plane.

Remote publication was intentionally out of scope. Existing foreign Work Lanes
were observed but not modified.

## Verification

Commands run from `work/binding-productization`:

```bash
uv run --group dev pytest tests/unit/test_workspace_lanes.py::test_workspace_status_reports_branch_worktree_bindings_without_ui_actions tests/unit/test_workspace_lanes.py::test_workspace_status_uses_configured_branch_role_policy tests/unit/test_workspace_lanes.py::test_prewrite_rejects_protected_lane_roles tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py::test_workspace_status_payload_validates_worktree_bindings tests/unit/test_schema_validation_and_gates.py::test_workspace_status_schema_rejects_ui_projection_fields tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_configured_role_and_binding_contracts -q
uv run --group dev pytest tests/unit/test_workspace_lanes.py tests/unit/test_cli_contracts.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_coupling_governance.py tests/architecture/test_product_design_contract.py -q
uv run --group dev pytest -q
uv run --group dev ruff check .
uv build --all-packages
uv run openspec validate --all --strict --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality coupling-audit --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos self audit --mode shape --json
```

Observed results:

- RED target set initially failed on missing `role_policy`, `submit_lane`,
  `binding_registry`, expanded vendor scanning, and product contract wording.
- Focused RED/GREEN target set: `9 passed`.
- Related workspace, CLI, schema, coupling, and product-contract tests:
  `118 passed`.
- Full pytest: `266 passed`.
- Ruff: all checks passed.
- Package build: all workspace packages built as sdist and wheel.
- OpenSpec strict validation: `8` specs passed, `0` failed.
- Schema quality: `ok=true`, `required_gaps=[]`.
- Coupling audit: `ok=true`, `required_gaps=[]`, with
  `data.binding_registry` classifying Git repository substrate and branch role
  policy as `product_semantic_hard_binding`, OpenSpec as
  `mandatory_governance_dependency`, command/schema/claim/evidence/local-state
  protocols as `native_protocol_binding`, current proof tools as
  `self_hosting_toolchain_binding`, and host/protocol projections as
  `profile_or_adapter_binding`.
- Claims quality: `ok=true`, `required_gaps=[]`, with
  `ethos-coupling-governance` bound to this evidence.
- Self audit shape mode: `ok=true`, `required_gaps=[]`.
