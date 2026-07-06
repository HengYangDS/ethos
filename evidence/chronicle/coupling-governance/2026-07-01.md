---
subject: ethos:evidence:coupling-governance
role: evidence
state: active
relations:
  supports: ethos-coupling-governance
---

# Coupling Governance Evidence - 2026-07-01

This evidence records the local ETHOS coupling-governance batch.

## Scope

- Preserved Git as a native ETHOS product substrate: commits, refs, branches,
  worktrees, HEAD binding, and branch roles remain product semantics.
- Removed GitLab release-file coupling from product release policy. GitLab is
  now the current host profile under `.ethos/release.toml`.
- Added `ethos quality coupling-audit --json` and wired it into
  `ethos self audit`.
- Added gate `profile` and `toolchain` metadata so current repository proof
  tools are self-hosting evidence, not product ontology.
- Updated adoption profile scaffolding so hosted CI projections are declared as
  host-profile surfaces.
- Updated canonical docs and machine-readable package ontology to distinguish
  Git-native semantics from hosted forge, editor, model, and toolchain
  providers.

Remote publication was intentionally out of scope. The foreign Work Lane
`work/product-migration-closure` was not entered, modified, retired, or cleaned.

## Verification

Commands run from `work/coupling-governance`:

```bash
uv run --group dev pytest tests/unit/test_release_policy_and_attestation.py tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py::test_gate_registry_classifies_self_hosting_toolchain_profile tests/unit/test_cli_contracts.py::test_quality_help_lists_canonical_commands tests/unit/test_cli_contracts.py::test_quality_determinism_commands_are_available tests/unit/test_cli_contracts.py::test_quality_coupling_audit_reports_git_native_boundary tests/unit/test_adoption_profiles.py::test_gitlab_profile_adds_ci_projection tests/architecture/test_product_design_contract.py::test_product_design_contract_canonizes_kernel_first_principles tests/architecture/test_product_design_contract.py::test_product_design_contract_keeps_git_native_not_generic_vcs -q
uv run --group dev pytest tests/unit/test_release_policy_and_attestation.py tests/unit/test_coupling_governance.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_cli_contracts.py tests/unit/test_adoption_profiles.py tests/unit/test_adopt_apply_sample.py tests/unit/test_self_audit_modes.py tests/unit/test_self_governance_depth.py tests/unit/test_self_evolution_ledger.py tests/architecture/test_product_design_contract.py tests/architecture/test_release_assets.py -q
uv run --group dev ruff check .
uv run --package ethos ethos quality coupling-audit --json
uv run --package ethos ethos self audit --mode shape --json
uv run --package ethos ethos quality release-policy --json
uv run --package ethos ethos quality release --json
uv run --package ethos ethos quality gates --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos quality docs-registry --json
uv run --group dev pytest -q
uv build --all-packages
uv run openspec validate --all --strict --json
uv run --package ethos ethos prove --execute --gate self-audit --gate claims --gate schemas --json
```

Observed results:

- Focused RED/GREEN target set: `15 passed`.
- Affected file-level suite: `109 passed`.
- Ruff: all checks passed.
- Coupling audit: `ok=true`, `required_gaps=[]`.
- Shape self-audit: `ok=true`, `required_gaps=[]`, with coupling included.
- Release policy: `ok=true`, product required files exclude `.gitlab*`, and
  host profile provider is `gitlab`.
- Gate registry: product gates use `profile=product`, self-hosting gates use
  `profile=self-hosting` and `toolchain=uv-python`.
- Schema validation: `ok=true`, including the expanded gate schema instance.
- Claim digest check: `ok=true`, including this evidence file.
- Docs registry: `ok=true`, with this evidence file registered.
- Full pytest: `249 passed`.
- Package build: all workspace packages built as sdist and wheel.
- OpenSpec strict validation: `10` items passed, `0` failed.
- Proof gates: `ok=true`, `state=proven`, `gate_count=3`.
