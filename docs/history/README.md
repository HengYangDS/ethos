---
subject: docs:history
role: index
state: canonical
relations:
  canonical_for: historical documentation
---

# History Documentation

Status: canonical.

Purpose: hold retired rationale, archival logs, and migration history without
letting older vocabulary override current ETHOS contracts.

See also: [Documentation Root](../README.md), [Governance Docs](../governance/README.md),
[Reference Docs](../reference/README.md).

## Curated routes

History is an index over retained rationale and completed change records; it is
not a current-state ledger or another evidence store.

| Need | Canonical record |
| --- | --- |
| Completed change carriers and their closeout material | [OpenSpec archive](../../openspec/changes/archive/) |
| Retired fixed-path documentation topology | [Documentation Topology Contract, 2026-07-08](docs-topology-contract-20260708.md) |
| External-adopter observation on 2026-07-14 | [Official Change archive](../../openspec/changes/archive/2026-07-14-current-candidate-head-real-adopter-evidence/) |
| External-adopter observation on 2026-07-13 | [Official Change archive](../../openspec/changes/archive/2026-07-13-current-product-head-real-adopter-evidence/) |

## Historical Evidence Retrieval

The historical evidence tree is retained at source commit
`06ea14f0ae9cfdf1e760ff8dc944b22c0b22361c`, tree
`a77f77462c487a7a9b7746f3e93b4bbdad8f51ce`. Retrieve exact bytes without
restoring a second workspace archive:

```bash
git ls-tree -r 06ea14f0ae9cfdf1e760ff8dc944b22c0b22361c -- evidence/
git show 06ea14f0ae9cfdf1e760ff8dc944b22c0b22361c:evidence/claims/current-head-real-adopter-evidence-20260714.toml
```

These are dated records, not the latest candidate or current proof. Historical
labels do not close unfinished obligations. Current product meaning belongs
to the product contract and official specifications; exact Git facts and
selected Attestations establish current implementation and proof.
