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

Purpose: replace lifecycle-labeled documentation lanes with a strict semantic
kernel owned by the explicit docs-topology capability.

See also: [Docs Topology](../../architecture/docs-topology.md),
[Decision Index](../decision-index.md), and
[Superseded DR-0002](../superseded/DR-0002-documentation-topology-isomorphism-contract.md).

## Record

| Field | Value |
| --- | --- |
| Decision ID | DR-0004 |
| Kind | governance |
| Decision Makers | Repository maintainers through accepted repository instruction; implemented by local ETHOS Work Lane. |
| Status | accepted |
| Decision Date | 2026-07-08 |
| Decision Version | 2 |
| Decision Change Date | 2026-07-20 |
| Record Review Date | 2026-10-08 |
| Supersedes | DR-0002 |
| Superseded By | None |
| Scope | The documentation topology checked by the explicit docs-topology capability and retirement readiness. |
| Boundary | Owns one strict docs kernel and rejects lifecycle state as physical topology; does not make documentation a bootstrap prerequisite. |
| Context | `docs/current/` and `docs/future/` encoded lifecycle state as directory structure, while full adoption scaffolding confused optional capability readiness with repository binding. |
| Decision | When docs-topology is executed, require one repository-form-invariant kernel and reject `current` and `future` as roots or state values. `ethos adopt` writes only `.ethos/profile.toml` and does not activate this capability. |
| Consequences | Product and adopter repositories may add domain roots, but no compatibility exception or alternate kernel exists. Missing docs carriers block only explicit docs-topology or retirement boundaries, not default adoption proof. |
| Proof or Evidence | `ethos prove --gate docs-topology --json`, focused strict-topology tests, retirement-readiness tests, and explicit HEAD-bound proof gate execution. |
| Revisit Trigger | Reopen only if evidence proves that a new minimal semantic recovery root is universally necessary without turning lifecycle state into topology. |

## Decision

The strict kernel is:

- `docs/README.md` for navigation;
- `docs/decisions/` for durable rulings;
- `docs/evidence/` for curated proof summaries;
- `docs/history/` for retired rationale and archival logs;
- `docs/reference/` for stable vocabulary and references.

This is semantic isomorphism, not a product-layout clone. Product or adopter
extension roots remain domain-owned and optional. ETHOS product extensions are
`docs/architecture/`, `docs/concepts/`, `docs/governance/`, `docs/plans/`,
`docs/research/`, and `docs/start/`; they are not part of the required kernel.
Single repositories, monorepos, and multi-repository subjects use the same
kernel whenever docs-topology is selected.

`current` and `future` are forbidden documentation roots and state values.
There is no profile compatibility policy, status mapping, migration exception,
shim, or alternate kernel. Governed lifecycle state uses explicit metadata plus
repository evidence.

Adoption binds a repository through `.ethos/profile.toml` only. The official
docs-topology command or retirement readiness activates this decision's strict
requirements; bootstrap does not create or claim them.
