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

See also: [Decision Index](decision-index.md).
