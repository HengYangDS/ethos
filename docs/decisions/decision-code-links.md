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
| [DR-0001](accepted/DR-0001-generated-artifact-topology-contract.md) | `system/policies/generated-artifact-topology.toml`, `system/policies/evidence-layout.toml`, `packages/ethos-core/src/ethos_core/data/generated_artifact_topology.toml`, `packages/ethos-core/src/ethos_core/data/evidence_layout.toml`, `packages/ethos-core/src/ethos_core/contracts/artifacts/topology.py`, `packages/ethos-core/src/ethos_core/contracts/evidence/layout.py`, `packages/ethos/src/ethos/repository/policy/artifacts.py`, `packages/ethos/src/ethos/repository/evidence/topology.py` | `tests/unit/governance/test_generated_artifact_topology.py`, `tests/unit/governance/test_evidence_topology.py`, `tests/unit/cli/test_generated_artifact_topology_cli.py`, `tests/architecture/test_evidence_layout.py`, `tests/architecture/test_generated_artifact_topology_docs.py`, `tests/architecture/test_declarative_runtime_spine.py` | `ethos quality generated-artifacts --json`, `ethos quality evidence-freshness --json` |
| [DR-0002](superseded/DR-0002-documentation-topology-isomorphism-contract.md) | Superseded historical record; see DR-0004 for active code ownership. | `tests/architecture/test_generated_artifact_topology_docs.py` | Historical only. |
| [DR-0004](accepted/DR-0004-native-documentation-topology-contract.md) | `packages/ethos-core/src/ethos_core/contracts/docs/topology.py`, `packages/ethos/src/ethos/repository/policy/docs/topology.py`, `packages/ethos/src/ethos/repository/adoption/scaffold/core.py`, `packages/ethos/src/ethos/repository/adoption/retirement.py` | `tests/unit/governance/test_docs_topology.py`, `tests/unit/cli/test_docs_topology_cli.py`, `tests/unit/adoption/test_retirement.py`, `tests/architecture/test_generated_artifact_topology_docs.py` | `ethos quality docs-topology --json`, `ethos fleet retirement-readiness --target <repo> --root <product> --json` |
| [DR-0003](accepted/DR-0003-proof-scope-compatibility-contract.md) | `packages/ethos/src/ethos/cli.py` | `tests/unit/cli/test_contracts.py::test_prove_accepts_proof_scope_compatibility_flag`, `tests/unit/cli/test_contracts.py::test_prove_accepts_host_probe_compatibility_flags_without_claiming_host_truth`, `tests/unit/cli/test_contracts.py::test_prove_rejects_unknown_proof_scope` | `ethos prove --scope proof-kernel --json`, `ethos prove --scope proof-kernel --host --probe --json` |
| Adopter local-state shadow parity compatibility | `packages/ethos/src/ethos/adapters/repo/status/bindings.py`, `docs/architecture/local-state.md` | `tests/unit/lanes/test_lanes.py::test_workspace_status_reads_control_root_json_lease_projection`, `tests/unit/lanes/test_lanes.py::test_workspace_status_prefers_sqlite_lease_over_json_projection`, `tests/unit/lanes/test_lanes.py::test_workspace_status_ignores_expired_json_lease_projection`, `tests/unit/product/parity` | `ethos parity shadow --adopter <id> --target <repo> --execute --write-evidence --json` |
| [DR-0006](accepted/DR-0006-proof-trust-boundary.md) | `packages/ethos/src/ethos/adapters/mutation/proof.py`, `packages/ethos/src/ethos/adapters/admission/evidence/external.py`, `packages/ethos-core/src/ethos_core/contracts/evidence/external.py` | `tests/unit/mutation/test_proof_forgery_honesty.py` | `ethos prove --execute --json` (local readiness); hosted/local independent-identity verification is optional and default-off |
| [DR-0007](accepted/DR-0007-docs-kernel-invariance-and-adopter-parity-locus.md) | `packages/ethos-core/src/ethos_core/contracts/docs/topology.py`, `packages/ethos/src/ethos/repository/evidence/shadow/routing.py`, `packages/ethos/src/ethos/repository/evidence/parity/core.py` | `tests/unit/policy/test_promotion_floor.py`, `tests/unit/product/parity` | `ethos quality docs-topology --json`; `ethos parity shadow --adopter <id> --target <repo> --execute --write-evidence --json` (adopter-side evidence) |

See also: [Decision Index](decision-index.md).
