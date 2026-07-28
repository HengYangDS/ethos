---
subject: ethos:decisions
role: index
state: canonical
relations:
  canonical_for: decision records
---

# Decision Records

Status: canonical.

Purpose: hold durable ETHOS product rulings that later agents must respect
before reopening architecture, governance, tooling, or process choices.

## Choose

| Need | Read |
| --- | --- |
| All current and superseded rulings | [Decision Index](decision-index.md) |
| Start a new decision record | [Decision Record Template](decision-record-template.md) |
| Review dependencies | [Decision Dependency Map](decision-dependency-map.md) |
| Review code and check links | [Decision Code Links](decision-code-links.md) |

## Boundary

Decision Records are flat `DR-*.md` files. Status is record metadata and index
data, never directory topology. Research discovers options; a Decision Record
selects; OpenSpec owns executable change requirements and tasks; implementation
realizes them; Attestations prove them.

Owns: durable rulings that later agents must cite before reopening a settled
judgment.

Does not own: routine task notes, proof transcripts, OpenSpec deltas, runtime
state, generated reports, or current runtime behavior.

See also: [Documentation Index](../index.md), [Product Design Contract](../governance/product-design-contract.md), and [Generated Artifact Topology](../architecture/generated-artifact-topology.md).
