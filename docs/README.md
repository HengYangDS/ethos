---
subject: docs:root
role: index
state: canonical
relations:
  canonical_for: ethos documentation physical shape
---

# ETHOS Documentation Root

Status: canonical.

Purpose: define ETHOS's own physical documentation shape without turning that
shape into an adopter contract or a second navigation index.

See also: [Product Index](index.md), [Docs Registry](governance/docs-registry.md),
[Evidence Docs](evidence/README.md), and [Reference Docs](reference/README.md).

## ETHOS Documentation Shape

| Lane | Owns |
| --- | --- |
| `evidence/` | Dated proof, manifests, smoke notes, and closeout records. |
| `reference/` | Stable vocabulary, boundaries, and governance references. |
| `history/` | Retired rationale and archival logs. |

## ETHOS Product Extensions

| Root | Owns |
| --- | --- |
| `architecture/` | Product architecture and contract explanations. |
| `governance/` | Product governance models and policies. |
| `concepts/`, `plans/`, `research/`, `guides/` | Product-specific explanation, planning, research, and onboarding. |

Truth state is document metadata, not path topology. Use the explicit
front matter vocabulary (`state: canonical`, `state: active`, `state: planned`,
`state: experimental`, `state: superseded`, or `state: archived`) to express
lifecycle. Do not use `current` or `future` as state values, and do not create
`current/` or `future/` documentation roots.

This shape describes ETHOS itself. It is not a mandatory physical layout for
adopters. Adopters use their profile-declared documentation root and the
portable Docs Registry contract.
