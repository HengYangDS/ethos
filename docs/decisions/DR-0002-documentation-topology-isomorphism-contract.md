---
subject: ethos:decision:documentation-topology-isomorphism-contract
role: decision
state: superseded
relations:
  canonical_for: documentation topology isomorphism decision
---

# DR-0002: Documentation Topology Isomorphism Contract

Status: superseded.

Purpose: record the durable ruling that ETHOS and governed repositories must
share a high-isomorphism documentation kernel before DR-0004 replaced `current`/`future` physical lanes with semantic roots.

See also: [Docs Topology](../../architecture/docs-topology.md),
[DR-0004](../DR-0004-native-documentation-topology-contract.md),
[Decision Index](../decision-index.md), and [Generated Artifact Topology](../../architecture/generated-artifact-topology.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0002 |
| Kind | governance |
| Decision Makers | Repository owner through accepted repository instruction on 2026-07-08; implemented by local ETHOS work lane. |
| Status | superseded |
| Decision Date | 2026-07-07 |
| Decision Version | 2 |
| Decision Change Date | 2026-07-08 |
| Record Review Date | 2026-10-07 |
| Supersedes | None |
| Superseded By | DR-0004 |
| Scope | Documentation information architecture across ETHOS and governed repositories. |
| Boundary | Owns the common docs kernel and decision-record surface across single repositories, monorepos, and multi-repository governed subjects; does not force identical subject matter, product extension roots, or adopter domain docs. |
| Context | External ETHOS must replace embedded adopter-local ETHOS without making agents relearn repository governance layout per adopter. |
| Decision | Require a shared semantic docs kernel with `start`, `governance`, `decisions`, `evidence`, `plans`, `history`, and `reference` lanes plus the complete `docs/decisions/` structure; forbid `current`/`future` roots such as `docs/current/` and `docs/future/`. |
| Consequences | `ethos adopt` scaffolds the kernel; `ethos quality docs-topology --json` audits it; `ethos fleet retirement-readiness` blocks embedded-backend retirement on docs-topology gaps; product-specific ETHOS roots remain extensions, not substitutes. |
| Proof or Evidence | `ethos quality docs-topology --json`, `ethos quality docs-registry --json`, focused docs topology tests, and HEAD-bound proof gate execution. |
| Revisit Trigger | Reopen only if a governed repository cannot preserve the common kernel without losing domain clarity or if a stronger common kernel is accepted. |

## Context

The external ETHOS product is adopter-neutral, while governed repositories need
recognizable governance, decision, evidence, reference, plans, and history
separation. If each repository uses a different documentation topology, agents
must infer governance from prose and stale local memory. That weakens retirement
of embedded ETHOS because capability parity would depend on repo-specific habits
rather than a product contract.

## Decision

Adopt the Documentation Topology Isomorphism Contract:

- every governed repository should expose `docs/README.md`, `docs/index.md`,
  `docs/start/`, `docs/governance/`, `docs/decisions/`, `docs/evidence/`,
  `docs/plans/`, `docs/history/`, and `docs/reference/` entrypoints;
- `docs/decisions/` must include `README.md`, `decision-index.md`,
  `decision-dependency-map.md`, `decision-code-links.md`, `accepted/README.md`,
  `superseded/README.md`, `templates/README.md`, and
  `decision-record-template.md`;
- repository form does not change the required kernel: single repositories,
  monorepos, and multi-repository governed subjects expose the same required
  docs paths;
- ETHOS product extension roots such as `docs/architecture/`, `docs/concepts/`,
  and `docs/research/` may remain, but they do not replace the common kernel;
- adopter repositories may add domain-specific docs while preserving the kernel;
- `docs/current/` and `docs/future/` are forbidden because they encode lifecycle
  state in topology instead of front matter, evidence, and promotion status;
- docs topology is audited by `ethos quality docs-topology --json` and included
  in proof gates;
- embedded ETHOS retirement readiness must include the same docs-topology audit
  for the adopter target and block on missing common-kernel paths.

## Consequences

`ethos adopt` must create the common docs kernel for new adopters. Existing
adopters such as reference-adopter can keep richer domain-specific documentation,
but external ETHOS retirement readiness must prove that the common semantic kernel,
decision-record surface, and forbidden-root checks are present and clean. Narrative assertions about docs
organization are not enough.

## Revisit Trigger

Revisit only if a real governed repository cannot preserve the common kernel
without losing domain clarity, or if a later ETHOS decision accepts a strictly
stronger shared semantic docs topology.

## Invariants

- Governance, decisions, evidence, plans, history, and references remain discoverable.
- Lifecycle state is not encoded by `current` or `future` directory names.
- Product extensions do not replace shared navigation semantics.

## Alternatives Considered

| Option | Verdict | Pros | Cons | Decision basis |
| --- | --- | --- | --- | --- |
| Fixed repository-form-invariant documentation kernel | superseded | Gives humans and agents predictable physical entrypoints. | Exports ETHOS's product layout into adopter contracts. | Physical sameness was stronger than semantic portability required. |
| Repository-owned layout with no shared semantic contract | rejected | Maximizes domain autonomy. | Makes discoverability and parity depend on prose and local memory. | It cannot provide machine-checkable governance discovery. |
| Portable metadata registry with repository-owned physical layout | selected replacement | Preserves semantic discoverability without imposing product topology. | Requires stronger metadata and taxonomy validation. | It preserves portable semantics while leaving physical form to the governed repository. |

## Selected Approach And Rationale

The historical choice favored a fixed kernel for discoverability. The current
selection is the portable Docs Registry plus repository-owned physical form.

## Proof Or Evidence

- Historical docs-topology records.
- Current [Docs Registry](../governance/docs-registry.md) validation.

## Decision Change Ledger

| Version | Date | Change | Reason | Evidence |
| --- | --- | --- | --- | --- |
| 2 | 2026-07-08 | Superseded by a smaller semantic topology | Reduce lifecycle-shaped paths | DR-0004 |
| 3 | 2026-07-28 | Recorded current portable-registry supersession | Separate semantic discovery from physical sameness | Docs Registry and terminal convergence |
