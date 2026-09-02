---
subject: docs:root
role: index
state: canonical
relations:
  canonical_for: ethos documentation physical shape
---

# ETHOS Documentation

Status: canonical.

Purpose: provide the one documentation entrypoint and explain ETHOS's own
physical documentation shape without turning that shape into an adopter
contract.

See also: [Quickstart](guides/quickstart.md),
[Product Design Contract](governance/product-design-contract.md),
[Terminal Governance Product Design](plans/terminal-governance-product-design.md),
and [Command Plane](reference/command-plane.md).

## Start Here

| Need | Read |
| --- | --- |
| First governed change | [Quickstart](guides/quickstart.md) |
| Current product meaning | [Product Design Contract](governance/product-design-contract.md) |
| Remaining convergence work | [Terminal Governance Product Design](plans/terminal-governance-product-design.md) |
| Public commands | [Command Plane](reference/command-plane.md) |
| Agent entry | [AGENTS.md](../AGENTS.md) and [Rules](../rules/README.md) |
| Adoption | [Adoption Profiles](architecture/adoption-profiles.md) |

## ETHOS Documentation Shape

| Lane | Owns |
| --- | --- |
| `decisions/` | Durable reasons for accepted or superseded design choices; never runtime authority. |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `reference/` | Stable vocabulary, boundaries, and governance references. |
| `history/` | Retired rationale and archival logs. |

## ETHOS Product Extensions

| Root | Owns |
| --- | --- |
| `architecture/` | Product architecture and contract explanations. |
| `governance/` | Product governance models and policies. |
| `concepts/`, `plans/`, `research/`, `guides/` | Product-specific explanation, planning, research, and onboarding. |

## Decision Rationale

These records preserve choices whose reasons are not fully recoverable from
current contracts alone. They do not own current behavior or workflow state.

- [Documentation portability](decisions/documentation-portability.md)
- [Proof trust boundary](decisions/proof-trust-boundary.md)
- [Source-budget non-compensation](decisions/source-budget-non-compensation.md)

Navigation for larger subject areas remains with their genuine directory
entrypoints: [Governance](governance/README.md), [Plans](plans/README.md),
[Reference](reference/README.md), [Evidence](evidence/README.md), and
[History](history/README.md).

Truth state is document metadata, not path topology. Use the explicit
front matter vocabulary (`state: canonical`, `state: active`, `state: planned`,
`state: experimental`, `state: superseded`, or `state: archived`) to express
lifecycle. Do not use `current` or `future` as state values, and do not create
`current/` or `future/` documentation roots.

This shape describes ETHOS itself. It is not a mandatory physical layout for
adopters. Adopters use their profile-declared documentation root and the
portable Docs Registry contract.
