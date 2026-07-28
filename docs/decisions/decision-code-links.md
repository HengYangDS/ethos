---
subject: ethos:decisions:code-links
role: reference
state: canonical
relations:
  canonical_for: decision code links
---

# Decision Code Links

Status: canonical.

Purpose: connect ETHOS Decision Records to code, tests, and command surfaces.

| Decision | Code | Tests | Command |
| --- | --- | --- | --- |
| [DR-0001](DR-0001-generated-artifact-topology-contract.md) | `system/policies/generated-artifact-topology.toml`, `system/policies/evidence-layout.toml`, `pyproject.toml`, `src/ethos/contracts/artifacts/topology.py`, `src/ethos/contracts/evidence/layout.py`, `src/ethos/repository/policy/artifacts.py`, `src/ethos/repository/policy/artifact_entrypoints.py`, `src/ethos/repository/evidence/topology.py` | `tests/unit/policy/test_artifacts.py`, `tests/architecture/test_declarative_governance_spine.py` | `ethos prove --gate generated-artifacts --json`, `ethos prove --gate evidence-freshness --json` |
| [DR-0002](DR-0002-documentation-topology-isomorphism-contract.md) | Historical only; see the [Docs Registry](../governance/docs-registry.md) for current documentation semantics. | Historical only. | Historical only. |
| [DR-0004](DR-0004-native-documentation-topology-contract.md) | Historical only; current ownership is the [Docs Registry](../governance/docs-registry.md) and ETHOS repository self-audit. | Historical only. | Historical only; the former `docs-topology` gate is retired. |
| [DR-0003](DR-0003-proof-scope-compatibility-contract.md) | `src/ethos/surface/cli/root/proof.py` | `tests/unit/cli/test_contracts_land.py::test_prove_scope_helpers_bind_known_and_unknown_scopes_without_host_claims`, `tests/unit/cli/test_contracts_land.py::test_prove_public_command_keeps_focused_host_probe_evidence_separate` | `ethos prove --scope proof-kernel --json`, `ethos prove --scope proof-kernel --host --probe --json` |
| Adopter local-state evidence boundary | `src/ethos/adapters/repo/status/bindings.py`, `docs/architecture/local-state.md` | `tests/unit/lanes/lease/test_lease_lifecycle.py` | `ethos prove --root <repo> --full --json` |
| [DR-0006](DR-0006-proof-trust-boundary.md) | `src/ethos/adapters/mutation/proof.py`, `src/ethos/adapters/mutation/proof_artifacts.py`, `src/ethos/adapters/mutation/proof_validation.py`, `src/ethos/adapters/admission/evidence/external.py`, `src/ethos/contracts/evidence/external.py` | `tests/unit/kernel/test_proof_plan_binding.py`, `tests/unit/admission/test_independent_verification.py` | `ethos prove --execute --json` (local readiness); independent-identity verification is optional and default-off |
| [DR-0007](DR-0007-docs-kernel-invariance-and-adopter-parity-locus.md) | Historical only; see the [Docs Registry](../governance/docs-registry.md) and Product Design Contract for active ownership. | Historical only. | Historical only. |
| [DR-0008](DR-0008-metric-domain-budget-contract.md) | Historical decision; current measurement is owned by `src/ethos/domain/source_budget/measurement.py` and `src/ethos/domain/source_budget/measurement_policy.py`. | `tests/unit/domain/test_source_budget.py` | `ethos prove --gate source-budget --json` |

See also: [Decision Index](decision-index.md).
