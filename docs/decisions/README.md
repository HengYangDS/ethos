---
subject: ethos:decisions
role: index
state: canonical
relations:
  canonical_for: decision record boundary and grammar
---

# Decision Records

Status: canonical.

Purpose: define what qualifies as a durable ETHOS ruling and route concrete
records through the one Decision Index.

## Choose

| Need | Read |
| --- | --- |
| Current rulings first, then historical rulings | [Decision Index](decision-index.md) |
| Start a new decision record | [Decision Record Template](decision-record-template.md) |

## Boundary

Decision Records are flat `DR-*.md` files. Status is record metadata and index
data, never directory topology. Research discovers options; a Decision Record
selects; OpenSpec owns executable change requirements and tasks; implementation
realizes them; Attestations prove them.

Owns: durable rulings that later agents must cite before reopening a settled
judgment.

Does not own: routine task notes, proof transcripts, OpenSpec deltas, runtime
state, generated reports, or current runtime behavior.

Each `DR-*.md` record owns its dependencies, implementation/evidence links,
alternatives, consequences, and revisit trigger. The index owns navigation and
orders accepted/proposed records by decision-change date descending before
superseded history. No dependency map or code-link ledger duplicates those
record-local facts.

See also: [Documentation Index](../index.md), [Product Design Contract](../governance/product-design-contract.md), and [Generated Artifact Topology](../architecture/generated-artifact-topology.md).
