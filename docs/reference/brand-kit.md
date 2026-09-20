---
subject: ethos:brand-kit
role: reference
state: active
relations:
  canonical_for: public identity assets and hosted-forge presentation
---

# ETHOS Brand Kit

Status: active.

Purpose: provide repository-owned source assets and factual usage rules for
ETHOS public presentation. These assets are a presentation layer; the Product
Design Contract remains the authority for product truth.

See also: [Product Design Contract](../governance/product-design-contract.md),
[Distribution](../architecture/distribution.md), and
[Reference Documentation](README.md).

## Canonical Files

| Use | File | Notes |
| --- | --- | --- |
| Square project image | [ethos-logo-1024.png](../../assets/brand/ethos-logo-1024.png) | Use where a forge or account accepts a square project image. |
| Editable master mark | [ethos-logo.svg](../../assets/brand/ethos-logo.svg) | Dark-background vector version. |
| Light-background mark | [ethos-logo-light.svg](../../assets/brand/ethos-logo-light.svg) | Use on paper or light surfaces. |
| One-color mark | [ethos-logo-mono.svg](../../assets/brand/ethos-logo-mono.svg) | Use where color is unavailable. |
| Wordmark lockup | [ethos-lockup-dark.svg](../../assets/brand/ethos-lockup-dark.svg) | Use in wide headers. |
| Social preview | [ethos-social-preview.png](../../assets/brand/ethos-social-preview.png) | Use where a forge accepts a repository social image. |
| Product poster | [ethos-poster.png](../../assets/brand/ethos-poster.png) | Use for long-form product introduction, not as an avatar. |

## Positioning

**ETHOS enables reliable repository evolution for people and interchangeable Agents.**

The product connects observed problems, research and intent alignment to capability
composition, collaboration and exploration, verification and delivery, actual
outcomes, feedback, recovery and exit. Its small trust kernel supports that full
path; a fixed CLI sequence is not the product definition.

The poster and social preview describe terminal design intent, not implemented
features, current installation availability or qualified release platforms.
Accepted intent, transient compilation, bounded effects and observed results have
distinct authority and lifetime. CLI, SDK, MCP and Skills share application meaning.

## Editable Sources And Native Rendering

The [poster master](../../assets/brand/ethos-poster.svg) and
[social master](../../assets/brand/ethos-social-preview.svg) are presentation
sources subordinate to the Product Design Contract. The PNGs retain the
established consumer paths and are rendered from those masters with native
librsvg; no bespoke drawing or image-generation runtime is required.

Run rsvg-convert with the corresponding SVG input and PNG output under
assets/brand. When product meaning changes, review visible wording against its
canonical owner, render and inspect the actual output at intended display sizes.
Preserve logo geometry unless the identity itself changes. SVG/PNG format checks
alone do not establish semantic accuracy, visual quality or hosted publication.

## Mark Rationale

The mark presents three repository-grounded ideas, not a feature map:

- **One origin** — a governed question is bounded before it becomes a change.
- **Two differentiated passages** — distinction is made only when it decides
  action; the paths remain inside the boundary.
- **One containing boundary** — evidence and claims retain scope; adapters do
  not become the semantic center.

The cinnabar datum is the single visual emphasis. It signals the point where a
claim must be bound to evidence, not a performance metric or status badge.

## Palette

| Token | Value | Use |
| --- | --- | --- |
| Ink | #10242C | Primary field and dark mark. |
| Paper | #F6F1E8 | Light field and high-contrast mark. |
| Cinnabar | #B5523D | Origin or datum only. |
| Muted | #687771 | Secondary explanatory text. |

Do not introduce gradients, neon glows, extra accent colors, badges, growth
metrics, or decorative East-Asian motifs. 问道 is the root constraint on
judgment, not a visual feature taxonomy.

## Hosted-Forge Boundary

Use the host's current repository or organization settings to apply the square
image or social preview. Host controls and labels may change independently of
this repository, so this document does not treat a specific UI route as
canonical.

Git history proves that the source assets exist. It does not prove that a
remote avatar, social preview, or project image has been applied.
