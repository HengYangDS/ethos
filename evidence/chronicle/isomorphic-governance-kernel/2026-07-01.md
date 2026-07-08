---
subject: ethos:evidence:isomorphic-governance-kernel
role: delivery-evidence
state: active
relations:
  supports: ethos-isomorphic-governance-kernel
---

# Isomorphic Governance Kernel Evidence - 2026-07-01

## Boundary

This batch is local-only. It does not push to a remote, does not create a
submit branch, does not advance the accepted root, and does not mutate other
agents' Work Lanes. The active Work Lane is
`work/complete-ethos-governance-productization`.

The product position is dual-form and isomorphic:

- `self-governance`: ETHOS governing the ETHOS repository.
- `product-adopter`: ETHOS governing another repository through an adopter
  profile.

Both forms reuse the same kernel chain and trust lifecycle:

```text
JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
Claim -> Boundary -> Carrier -> Evidence -> Decision -> Promotion
```

Only authority binding, profile configuration, adapter binding, strictness, and
rollout policy differ.

## Implemented Contracts

- Added `governance-profile.schema.json` as a provider-neutral contract for the
  dual-form governance profile report.
- Added `ethos_repository.governance_profiles.governance_profile_report()` with
  shared kernel chain, trust lifecycle, capability graph, run steps, truth
  sources, advisory projections, and explicit allowed differences.
- Registered the governance profile contract in schema validation so
  `ethos quality schemas`, `ethos self audit`, `ethos prove`, and `ethos report`
  consume the same contract path.
- Updated product, adoption, and schema documentation to state the
  `self-governance` / `product-adopter` positioning.
- Completed the OpenSpec carrier under
  `openspec/changes/isomorphic-governance-kernel/`.

## TDD Evidence

Initial RED checks:

```text
uv run --group dev pytest tests/unit/test_governance_profiles.py -q
result: failed as expected with KeyError: 'kernel_chain'

uv run --group dev pytest tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_isomorphic_governance_profiles -q
result: failed as expected because product docs lacked product-adopter wording
```

Focused GREEN checks:

```text
uv run --group dev pytest tests/unit/test_governance_profiles.py -q
result: 3 passed

uv run --group dev pytest tests/architecture/test_product_design_contract.py::test_product_design_contract_defines_isomorphic_governance_profiles -q
result: 1 passed

uv run --group dev pytest tests/unit/test_schema_validation_and_gates.py::test_schema_validation_report_covers_all_ethos_schemas tests/unit/test_governance_profiles.py -q
result: 4 passed

uv run --package ethos ethos quality schemas --json
result: ok=true, state=clean, schema_count=31, required_gaps=[]
```

## Final Local Verification

Pre-digest verification:

```text
uv run openspec validate --all --strict --json
result: 9 items passed, 0 failed

uv run --package ethos ethos quality docs-registry --json
result: ok=true, document_count=51, required_gaps=[]

uv run --package ethos ethos quality command-registry --json
result: ok=true, known_command_count=20, required_gaps=[]

uv run --package ethos ethos quality command-examples --json
result: ok=true, required_gaps=[]

uv run --group dev ruff check .
result: All checks passed.

uv run --group dev pytest tests/unit/test_cli_contracts.py::test_quality_help_lists_canonical_commands tests/unit/test_docs_registry.py::test_command_examples_do_not_leak_retired_roots -q
result: 2 passed
```

Post-digest verification commands run against this sealed evidence file:

```text
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos self audit --mode shape --json
uv run --group dev pytest tests/unit tests/architecture -q
uv run --package ethos ethos prove --full --execute --json
```

The final digest is recorded in
`claims/ethos-isomorphic-governance-kernel.toml`.
