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
| [DR-0001](accepted/DR-0001-generated-artifact-topology-contract.md) | `packages/ethos-core/src/ethos_core/contracts/generated_artifact_topology.py`, `packages/ethos/src/ethos/repository/policy/artifacts.py` | `tests/unit/governance/test_generated_artifact_topology.py`, `tests/unit/cli/test_generated_artifact_topology_cli.py`, `tests/architecture/test_generated_artifact_topology_docs.py` | `ethos quality generated-artifacts --json` |
| [DR-0002](accepted/DR-0002-documentation-topology-isomorphism-contract.md) | `packages/ethos-core/src/ethos_core/contracts/docs_topology.py`, `packages/ethos/src/ethos/repository/policy/docs_topology.py`, `packages/ethos/src/ethos/repository/adoption/scaffold.py`, `packages/ethos/src/ethos/repository/adoption/retirement.py` | `tests/unit/governance/test_docs_topology.py`, `tests/unit/cli/test_docs_topology_cli.py`, `tests/unit/adoption/test_retirement.py`, `tests/architecture/test_generated_artifact_topology_docs.py` | `ethos quality docs-topology --json`, `ethos fleet retirement-readiness --target <repo> --root <product> --json` |
| Adopter local-state shadow parity compatibility | `packages/ethos/src/ethos/adapters/repo/status_bindings.py`, `docs/architecture/local-state.md` | `tests/unit/lanes/test_lanes.py::test_workspace_status_reads_control_root_json_lease_projection`, `tests/unit/lanes/test_lanes.py::test_workspace_status_prefers_sqlite_lease_over_json_projection`, `tests/unit/lanes/test_lanes.py::test_workspace_status_ignores_expired_json_lease_projection`, `tests/unit/product/test_parity_generic.py` | `ethos parity shadow --adopter <id> --target <repo> --execute --write-evidence --json` |

See also: [Decision Index](decision-index.md).
