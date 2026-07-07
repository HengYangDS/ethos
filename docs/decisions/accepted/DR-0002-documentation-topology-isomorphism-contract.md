---
subject: ethos:decision:documentation-topology-isomorphism-contract
role: decision
state: canonical
relations:
  canonical_for: documentation topology isomorphism decision
---

# DR-0002: Documentation Topology Isomorphism Contract

Status: accepted.

Purpose: record the durable ruling that ETHOS and governed repositories must
share a high-isomorphism documentation kernel.

See also: [Docs Topology](../../architecture/docs-topology.md),
[Decision Index](../decision-index.md), and [Generated Artifact Topology](../../architecture/generated-artifact-topology.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0002 |
| Kind | governance |
| Decision Makers | Repository owner through current chat instruction; implemented by local ETHOS work lane. |
| Status | accepted |
| Decision Date | 2026-07-07 |
| Decision Version | 1 |
| Decision Change Date | 2026-07-07 |
| Record Review Date | 2026-10-07 |
| Supersedes | None |
| Superseded By | None |
| Scope | Documentation information architecture across ETHOS and governed repositories. |
| Boundary | Owns the common docs kernel and decision-record surface across single repositories, monorepos, and multi-repository governed subjects; does not force identical subject matter, product extension roots, or adopter domain docs. |
| Context | External ETHOS must replace embedded adopter-local ETHOS without making agents relearn repository governance layout per adopter. |
| Decision | Require a shared docs kernel with `current`, `decisions`, `evidence`, `future`, `history`, and `reference` lanes plus the complete `docs/decisions/` structure. |
| Consequences | `ethos adopt` scaffolds the kernel; `ethos quality docs-topology --json` audits it; product-specific ETHOS roots remain extensions, not substitutes. |
| Proof or Evidence | `ethos quality docs-topology --json`, `ethos quality docs-registry --json`, focused docs topology tests, and HEAD-bound proof gate execution. |
| Revisit Trigger | Reopen only if a governed repository cannot preserve the common kernel without losing domain clarity or if a stronger common kernel is accepted. |

## Context

The external ETHOS product is adopter-neutral, while governed repositories need
recognizable authority, decision, evidence, reference, and future/current
separation. If each repository uses a different documentation topology, agents
must infer governance from prose and stale local memory. That weakens retirement
of embedded ETHOS because capability parity would depend on repo-specific habits
rather than a product contract.

## Decision

Adopt the Documentation Topology Isomorphism Contract:

- every governed repository should expose `docs/README.md`, `docs/current/`,
  `docs/decisions/`, `docs/evidence/`, `docs/future/`, `docs/history/`, and
  `docs/reference/` entrypoints;
- `docs/decisions/` must include `README.md`, `decision-index.md`,
  `decision-dependency-map.md`, `decision-code-links.md`, `accepted/README.md`,
  `superseded/README.md`, `templates/README.md`, and
  `templates/decision-record.md`;
- repository form does not change the required kernel: single repositories,
  monorepos, and multi-repository governed subjects expose the same required
  docs paths;
- ETHOS product extension roots such as `docs/architecture/` and
  `docs/governance/` may remain, but they do not replace the common kernel;
- adopter repositories may add domain-specific docs while preserving the kernel;
- docs topology is audited by `ethos quality docs-topology --json` and included
  in proof gates.

## Consequences

`ethos adopt` must create the common docs kernel for new adopters. Existing
adopters such as alphasim-dmgr can keep richer domain-specific documentation,
but external ETHOS retirement readiness must prove that the common kernel and
decision-record surface are present and current. Narrative assertions about docs
organization are not enough.

## Revisit Trigger

Revisit only if a real governed repository cannot preserve the common kernel
without losing domain clarity, or if a later ETHOS decision accepts a strictly
stronger shared docs topology.
