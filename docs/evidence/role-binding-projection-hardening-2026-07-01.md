---
subject: ethos:evidence:role-binding-projection-hardening
role: evidence
state: active
relations:
  supports: ethos-role-binding-projection-hardening
---

# Role Binding Projection Hardening Evidence - 2026-07-01

This evidence records the local ETHOS role-binding and projection-hardening
batch.

## Scope

- Added coupling-audit coverage for branch role policy provenance:
  `.ethos/workspace.toml`, config keys, default-policy state, semantic role
  order, and configured patterns are now machine-readable.
- Kept branch roles semantically distinct:
  release_root -> accepted_root -> candidate -> work_lane -> submit_lane.
  Release and accepted roots are both protected, but they are not collapsed into
  one role.
- Added a product-semantic binding registry entry for the standard Work Lane
  lifecycle command contract: `ethos lane start`, `ethos lane bind-claim`,
  `ethos land`, and `ethos lane retire-landed`.
- Added a coupling-audit required gap for host projection labels such as
  host-specific worktree navigation and branch navigation text in product
  semantic docs.
- Kept Git as the ETHOS product substrate. OpenSpec remains mandatory
  governance, not a product substrate and not a second command plane.
- Updated the coupling-audit schema, command-plane docs, product design
  contract, runner/mutation docs, schema-validation docs, and canonical
  OpenSpec specs to reflect the narrowed semantics.

Remote publication was intentionally out of scope. Existing foreign Work Lanes
were observed through status output but not read, modified, landed, or retired.

## Verification

Commands run from `work/role-binding-projection-hardening`:

```bash
uv run --group dev pytest tests/unit/test_coupling_governance.py -q
uv run --group dev pytest tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py::test_coupling_audit_payload_validates_binding_registry_contract tests/unit/test_schema_validation_and_gates.py::test_coupling_audit_schema_rejects_ui_projection_fields -q
uv run --group dev pytest tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py::test_coupling_audit_payload_validates_binding_registry_contract tests/unit/test_schema_validation_and_gates.py::test_coupling_audit_schema_rejects_ui_projection_fields tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_configured_role_and_binding_contracts tests/architecture/test_product_design_contract.py::test_canonical_product_docs_are_provider_neutral -q
uv run --package ethos ethos quality coupling-audit --json
uv run --package ethos ethos quality schemas --json
uv run --group dev ruff check packages/ethos-repository/src/ethos_repository/coupling.py tests/unit/test_coupling_governance.py tests/architecture/test_product_design_contract.py
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
uv run --package ethos ethos campaign closeout --adopter alphasim-dmgr --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --json
```

Observed results:

- RED coupling test run failed as expected with 5 failed / 5 passed: missing
  branch role provenance fields, missing Work Lane lifecycle registry binding,
  and missing host projection label gaps.
- GREEN focused coupling and schema run: `12 passed`.
- Focused coupling, schema, and product-contract run: `14 passed`.
- Coupling audit: `ok=true`, `required_gaps=[]`, and the
  `coupling-audit.schema.json` diagnostic passed.
- Schema quality: `ok=true`, `schema_count=25`, `required_gaps=[]`, and the
  `coupling-audit-contract` instance passed.
- Focused Ruff: all checks passed.
- Full pytest: `289 passed in 72.78s`.
- Full Ruff: all checks passed.
- Package build: all workspace packages built as sdist and wheel.
- OpenSpec strict validation: `8` specs passed, `0` failed.
- Self audit shape mode: `ok=true`, `required_gaps=[]`.
- Report: `ok=true`, score `15/15`, `product_gap_count=0`, and
  `parity_pending_count=0`.
- Release policy: `ok=true`, `required_gaps=[]`.
- Claim quality: `ok=true`, `required_gaps=[]`, and
  `ethos-role-binding-projection-hardening` pointed to this evidence record.
- Proof kernel after claim binding: `ok=true`, `state=proven`, `gate_count=3`,
  `required_gaps=[]`, and evidence digest
  `f7d535492c4e36a99f7b38283a4814bed654b551a7db068d4809cea65faa06fa`.
- Campaign closeout after claim binding: `ok=true`, `state=local_ready`,
  `remote_state=deferred`, `claim_binding=bound`, and `required_gaps=[]`.
  Before commit, its local closeout package still reported `work_lane_dirty`;
  this is expected and is cleared by committing before `ethos land --apply`.

Land, accepted-root fast-forward, and lane retirement are recorded by the final
local closeout steps.
