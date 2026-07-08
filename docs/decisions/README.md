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
| Accepted durable rulings | [Decision Index](decision-index.md) |
| Accepted record files | [Accepted Decisions](accepted/README.md) |
| Superseded record files | [Superseded Decisions](superseded/README.md) |
| Start a new decision record | [Decision Record Template](templates/decision-record.md) |
| Review dependencies | [Decision Dependency Map](decision-dependency-map.md) |
| Review code and check links | [Decision Code Links](decision-code-links.md) |

## Boundary

Owns: durable rulings that later agents must cite before reopening a settled
judgment.

Does not own: routine task notes, proof transcripts, OpenSpec deltas, runtime
state, generated reports, or current runtime behavior.

Decision Records are not a separate truth lane. They bind a decision to scope,
boundary, proof, consequences, and revisit triggers; promoted truth still lands
in code, tests, package metadata, canonical docs, reference docs, or dated
evidence.

See also: [Documentation Index](../index.md), [Product Design Contract](../governance/product-design-contract.md), and [Generated Artifact Topology](../architecture/generated-artifact-topology.md).
