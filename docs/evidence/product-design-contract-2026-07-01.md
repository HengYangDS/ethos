---
subject: ethos:product-design-contract-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/architecture, tests/unit, OpenSpec, self-audit
---

# Product Design Contract Evidence - 2026-07-01

## Scope

This evidence records the `ethos-product-design-contract` campaign slice.

Implemented changes:

- Added the canonical ETHOS product design contract.
- Added the target package ontology for the seven Python product packages:
  `ethos-core`, `ethos-contracts`, `ethos-repository`,
  `ethos-assistants`, `ethos-adapters`, `ethos`, and `ethos-test`.
- Added the product boundary convergence policy between the ETHOS product
  repository and the alphasim-dmgr adopter/reference repository.
- Added the capability parity ledger for embedded-to-product migration.
- Updated documentation navigation so these canonical docs are discoverable.
- Updated self-audit so the new design contract documents are required.
- Updated self-audit so target package ontology is visible without claiming the
  migration is already physically complete.
- Added read-only `ethos intake status` so the documented intake surface exists
  without binding product core to a specific adopter ledger provider.
- Added `ethos playbooks route --changed` as a changed-scope routing alias for
  documented shadow parity flows.
- Archived the completed `ethos-product-design-contract` OpenSpec change with
  the official OpenSpec CLI, promoting its requirement to the canonical
  `ethos-governance` spec.
- Responded to read-only implementation review by:
  - Routing `changed-scope` through the skill activation policy instead of
    silently falling back to the first playbook.
  - Treating an empty `.ethos/intake.toml` as invalid because it lacks an
    explicit ledger provider.
  - Keeping `target_package_ontology.ok=false` until the physical target
    package split exists, while recording `contract_ok=true`.
  - Syncing README terminology to `Evidence-grounded` and the
    `Constitution -> Subject -> Contract -> IR -> Transition -> Inscription ->
    Evidence -> Chronicle -> Evolution` kernel chain.
  - Syncing command-plane docs and canonical OpenSpec requirements for the new
    intake and changed-scope playbook surfaces.
- Responded to final pre-merge review by:
  - Removing the generic playbook route fallback so `--changed` requires an
    explicit `changed-scope` subject in activation metadata.
  - Adding negative regression tests for missing changed-scope activation and
    for skill id / subject substring matches that do not explicitly declare
    `changed-scope`.
  - Renaming the migration-stage package ontology output fields so current
    migration hosts are not confused with physically complete target packages.
  - Aligning the archived OpenSpec proposal and tasks with the runtime CLI
    surfaces that were actually added.

## Verification

Commands run from the isolated worktree:

```bash
uv run --group dev pytest -q tests/architecture/test_product_design_contract.py
uv run --group dev pytest -q tests/unit/test_self_governance_depth.py tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/unit/test_cli_contracts.py::test_report_scorecard_is_derived_from_governance_checks tests/unit/test_cli_contracts.py::test_self_evolution_loop_commands_are_available
uv run --package ethos ethos self audit --json
openspec archive ethos-product-design-contract --yes --json
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_intake_status_is_public_read_only_surface tests/unit/test_cli_contracts.py::test_quality_command_registry_rejects_retired_public_roots
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_playbooks_route_accepts_changed_scope_alias
uv run --package ethos ethos intake status --json
uv run --package ethos ethos playbooks route --changed --json
uv run --package ethos ethos quality command-surface --json
uv run --group dev pytest -q
uv run --group dev ruff check .
openspec validate --all --strict --json
uv run --package ethos ethos prove --execute --gate self-audit --gate claims --gate schemas --json
uv build --all-packages
npm run ethos -- --version
npm run test:npm -- --json
uv run --package ethos ethos report --json
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_playbooks_route_accepts_changed_scope_alias tests/unit/test_cli_contracts.py::test_intake_status_is_public_read_only_surface tests/unit/test_cli_contracts.py::test_intake_status_rejects_empty_configuration tests/unit/test_cli_contracts.py::test_quality_command_registry_rejects_retired_public_roots tests/architecture/test_product_design_contract.py::test_product_design_contract_is_self_audited_with_target_ontology
uv run --group dev pytest -q tests/unit/test_docs_registry.py tests/architecture/test_product_boundaries.py
uv run --package ethos ethos quality command-examples --json
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_playbooks_changed_scope_route_requires_explicit_subject
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_playbooks_changed_scope_route_requires_explicit_subject tests/unit/test_cli_contracts.py::test_playbooks_route_accepts_changed_scope_alias tests/unit/test_cli_contracts.py::test_self_audit_reports_product_shape tests/architecture/test_product_design_contract.py tests/unit/test_self_governance_depth.py
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_playbooks_changed_scope_route_ignores_id_and_subject_substrings
uv run --group dev pytest -q tests/unit/test_cli_contracts.py::test_playbooks_changed_scope_route_ignores_id_and_subject_substrings tests/unit/test_cli_contracts.py::test_playbooks_changed_scope_route_requires_explicit_subject tests/unit/test_cli_contracts.py::test_playbooks_route_accepts_changed_scope_alias
```

Observed results:

- Product design contract architecture tests: `5 passed`.
- Focused self-governance and CLI tests: `5 passed`.
- Official OpenSpec archive: `archivedAs=2026-06-30-ethos-product-design-contract`,
  `specsUpdated=true`, `added=1`.
- Intake status and command registry regression tests: `2 passed`.
- Playbooks changed-scope route regression test: `1 passed`.
- `ethos intake status --json`: `ok=true`, `state=unconfigured`,
  `truth_boundary=adopter-ledger`.
- `ethos playbooks route --changed --json`: `ok=true`,
  `subject=changed-scope`.
- `ethos quality command-surface --json`: `ok=true`, no required gaps, and
  `ethos intake` is listed as public command.
- Full test suite: `134 passed in 120.09s`.
- Ruff: all checks passed.
- OpenSpec strict validation: `9 passed / 0 failed`.
- Executed proof gate: `ok=true`, no required gaps, local proof digest emitted.
- `uv build --all-packages`: all six current migration-host Python packages
  built wheel and sdist artifacts locally.
- npm launcher smoke: `0.1.0a1`.
- npm pack dry run for `@agentic-workflow/ethos`: three packaged files,
  `README.md`, `bin/ethos.mjs`, and `package.json`.
- `ethos report --json`: score `14 / 14`, no required gaps.
- Review follow-up focused tests: `5 passed`.
- Docs registry and product boundary regression tests: `22 passed`.
- Command examples quality check: `ok=true`.
- Changed-scope route negative regression: failed before the route fallback fix,
  then passed after removing the fallback.
- Final focused review regression set: `10 passed`.
- Strict changed-scope route negative regression: failed before exact subject
  enforcement, then passed after `--changed` required explicit subject metadata.
- Strict changed-scope route regression set: `3 passed`.
