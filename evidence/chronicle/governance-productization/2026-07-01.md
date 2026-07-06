---
subject: evidence:governance-productization
role: delivery-evidence
state: active
relations:
  supports: ethos-lifecycle-productization
---

# Governance Productization Evidence

This evidence records the batch that closes ETHOS governance productization:
proof state semantics, active claim trust envelopes, OpenSpec lifecycle carrier
review, Work Lane claim-binding projection, intake projection boundaries,
provider-neutral schemas, capability profiles, scaffold coverage, and reference
adopter parity boundaries.

## Implemented Product Contracts

- `ethos prove --json` reports readiness, not proof, when gates are planned but
  not executed.
- `ethos prove --execute --json` reports proven only from executed passing gate
  runs.
- Active claims emit trust envelopes with boundary, evidence, OpenSpec carrier,
  fallback, kill signal, promotion targets, and required gaps.
- `ethos self openspec --lifecycle --json` composes official OpenSpec CLI
  validation with ETHOS lifecycle carrier checks.
- Work Lane status projects `claim_id` and `claim_binding` without treating lane
  presence as promotion.
- Existing Work Lanes can bind a trust-bearing claim through
  `ethos lane bind-claim --claim-id <claim> --apply` without recreating the
  lane or promoting lane presence into repository truth.
- Campaign closeout includes trust closeout and intake projection packages.
- `trust-envelope.schema.json`, `promotion-target.schema.json`, and
  `capability-profile.schema.json` are product schemas validated by
  `ethos quality schemas`.
- Canonical OpenSpec capability families include `capability.toml` profiles.

## Verification

```bash
uv run --group dev pytest tests/unit/test_schema_validation_and_gates.py -q
result: 15 passed

uv run --group dev pytest tests/unit/test_schema_validation_and_gates.py tests/unit/test_claims_governance.py tests/unit/test_workspace_lanes.py tests/unit/test_cli_contracts.py tests/unit/test_openspec_native_cache.py tests/unit/test_parity_command.py -q
result: 157 passed

uv run --group dev pytest tests/unit/test_adopt_apply_sample.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_workspace_lanes.py tests/unit/test_cli_contracts.py tests/unit/test_governance_lifecycle_fixtures.py tests/architecture/test_product_design_contract.py -q
result: 127 passed

uv run --package ethos ethos quality schemas --json
result: ok=true, schema_count=24, capability_profile_count=8

uv run --group dev ruff check .
result: All checks passed.

uv run --group dev pytest tests/unit tests/architecture -q
result: 276 passed

openspec validate --all --strict --json
result: 9 items passed, 0 failed

uv build --all-packages
result: built wheel and source distributions for ethos, ethos-adapters,
ethos-assistants, ethos-contracts, ethos-core, ethos-repository, and ethos-test

uv run --package ethos ethos quality claims --json
result: ok=true, state=clean

uv run --package ethos ethos self openspec --lifecycle --json
result: ok=true, state=clean, claim_binding=true

uv run --package ethos ethos lane bind-claim --claim-id ethos-lifecycle-productization --apply --json
result: ok=true, state=bound, branch=work/complete-ethos-governance-productization,
claim_id=ethos-lifecycle-productization

openspec archive complete-ethos-governance-productization --yes --json
result: archivedAs=2026-07-01-complete-ethos-governance-productization,
specsUpdated=true, added=15, modified=0, removed=0, renamed=0
```

The final closeout proof command is `uv run --package ethos ethos prove --full
--execute --json`; the active claim lists that command as required executed
proof evidence and the final claims gate verifies this file's digest.
