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
| Change carriers retained in the current tree | [OpenSpec archive](../../openspec/changes/archive/) |
| Retired fixed-path documentation topology | [Documentation Topology Contract, 2026-07-08](docs-topology-contract-20260708.md) |
| Retired current-tree Change carriers | Recover their exact Git revision as described below; current behavior belongs to [canonical specs](../../openspec/specs/). |

An archived Change is history, not a source of current requirements. The
accepted `97196e96dd115f430e8dbb72af39f50b71d98a90` snapshot retains every
pre-September 2026 archived carrier. Once its current-tree copy retires,
inspect the selected object at that exact historical revision:

```bash
git ls-tree -r 97196e96dd115f430e8dbb72af39f50b71d98a90 -- openspec/changes/archive/
git show 97196e96dd115f430e8dbb72af39f50b71d98a90:openspec/changes/archive/2026-07-13-current-product-head-real-adopter-evidence/proposal.md
```

Verify the selected commit and path before using those bytes as historical
evidence. Current-tree retirement requires Git reachability and recovery
checks; this route gives old tasks and deltas no current authority.

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

## Terminal Plan Observations

The execution narrative formerly mixed into the terminal plan's current entry
remains in Git at `bac03b71c9771de27206385a70ae17e85dccb4f0`, blob
`f2f7c6850ea75595ff2a873b79d69fd053af5ae0`:

```bash
git show bac03b71c9771de27206385a70ae17e85dccb4f0:docs/plans/terminal-governance-product-design.md
```

Use it for dated observations and discarded schedules, not current status.
Still-valid obligations remain in the product contract, active OpenSpec and
the terminal plan. This reference adds no workspace history copy or task ledger.
