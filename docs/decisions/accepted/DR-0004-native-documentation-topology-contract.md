---
subject: ethos:decision:native-documentation-topology-contract
role: decision
state: canonical
relations:
  canonical_for: minimal semantic documentation topology decision
  supersedes: DR-0002
---

# DR-0004: Minimal Semantic Documentation Topology Contract

Status: accepted.

Purpose: replace `current`/`future` documentation lanes with a minimal
minimal semantic kernel that matches ETHOS product semantics.

See also: [Docs Topology](../../architecture/docs-topology.md),
[Decision Index](../decision-index.md), and
[Superseded DR-0002](../superseded/DR-0002-documentation-topology-isomorphism-contract.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0004 |
| Kind | governance |
| Decision Makers | Repository owner through 2026-07-08 chat instruction; implemented by local ETHOS Work Lane. |
| Status | accepted |
| Decision Date | 2026-07-08 |
| Decision Version | 1 |
| Decision Change Date | 2026-07-08 |
| Record Review Date | 2026-10-08 |
| Supersedes | DR-0002 |
| Superseded By | None |
| Scope | Documentation information architecture across ETHOS and governed repositories. |
| Boundary | Owns the common docs kernel and decision-record surface; does not make lifecycle state a physical documentation root. |
| Context | `docs/current/` and `docs/future/` encoded lifecycle state as directory structure, weaker than ETHOS' authority, evidence, decision, reference, and history boundaries. |
| Decision | Remove `current` and `future` from the required physical docs kernel and reject them as documentation `state` values. Prove present repository truth through HEAD-bound proof and preserve unlanded intent in OpenSpec changes, plans, research, or decision revisit triggers. |
| Consequences | `ethos adopt` scaffolds the minimal semantic kernel; `ethos quality docs-topology --json` audits it; product or adopter docs may add domain roots without turning state labels into truth lanes. |
| Proof or Evidence | `ethos quality docs-topology --json`, focused docs topology tests, scaffold tests, and HEAD-bound proof gate execution. |
| Revisit Trigger | Reopen only if a governed repository needs a new minimal semantic root to preserve clarity without turning lifecycle state into a directory. |

## Decision

The common docs kernel is:

- `docs/README.md` for navigation;
- `docs/decisions/` for durable rulings;
- `docs/evidence/` for curated proof summaries;
- `docs/history/` for retired rationale and archival logs;
- `docs/reference/` for stable vocabulary and references.

ETHOS product extension roots include `docs/architecture/`, `docs/concepts/`,
`docs/governance/`, `docs/plans/`, `docs/research/`, and `docs/start/`.
Adopter repositories may add their own domain roots without weakening the
common kernel.

`current` and `future` are forbidden as documentation `state` values and
forbidden as physical docs roots. They may appear only as ordinary prose when
describing the rejected anti-pattern; governed lifecycle state uses the explicit
state vocabulary (`canonical`, `active`, `planned`, `experimental`,
`superseded`, `archived`) plus HEAD-bound evidence.
