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

Decision Records are flat files named
`DR-<four-digit-id>-<lower-kebab-description>.md`. Their closed lifecycle is
`proposed → accepted → superseded | retired`: `superseded` names exactly one
successor DR and that successor names the predecessor; `retired` ends a ruling
without pretending that another DR replaced it. Status is record metadata and
index data, never directory topology. Research discovers options; a Decision
Record selects; OpenSpec owns executable change requirements and tasks;
implementation realizes them; Attestations prove them.

Owns: durable rulings that later agents must cite before reopening a settled
judgment.

Does not own: routine task notes, proof transcripts, OpenSpec deltas, runtime
state, generated reports, or current runtime behavior.

Each DR owns its dependencies, supersession edges, implementation/evidence
links, alternatives, consequences, and revisit trigger. Every referenced DR
must exist, supersession is reciprocal, and dependency cycles are invalid. The
index is a complete derived projection: it links every DR exactly once and
orders accepted/proposed records by decision-change date descending before
superseded/retired history. No dependency map or code-link ledger duplicates
those record-local facts.

See also: [Documentation Index](../index.md), [Product Design Contract](../governance/product-design-contract.md), and [Generated Artifact Topology](../architecture/generated-artifact-topology.md).
