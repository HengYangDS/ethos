---
subject: docs:governance
role: index
state: canonical
relations:
  canonical_for: governance documentation
---

# Governance Documentation

Status: canonical.

Purpose: route ETHOS policies, operating constraints, product governance, and
repository boundary documents through a semantic docs root.

See also: [Documentation Root](../README.md),
[Product Design Contract](product-design-contract.md), [Forge Provider Contract](forge-provider-contract.md),
[Docs Registry](docs-registry.md), and [Reference Docs](../reference/README.md).

Governance docs are canonical only when their front matter says so and their
claims are backed by higher-authority source, tests, schemas, package metadata,
OpenSpec records, Commitments, Attestations, or evidence. Planned material
belongs under `docs/plans/` with `state: planned` until promoted.

## Meaning And Authority

| Reader question | Start here |
| --- | --- |
| What is ETHOS responsible for? | [Product Design Contract](product-design-contract.md) |
| What establishes a judgment, and what is only a projection? | [Authority](authority.md) |
| Where do accepted intent and Change progress live? | [OpenSpec Governance](openspec-governance.md) |
| What does evidence establish, and what does it not authorize? | [Provenance And Attestation](provenance-and-attestation.md) |
| How does feedback connect research and Changes? | [Learning And Change Relations](evolution-campaign.md) |

## Operation And Boundaries

| Reader question | Start here |
| --- | --- |
| Which constraints apply to a repository? | [Repository Profile Contract](repository-profile-contract.md) |
| What stays with the product versus the adopter? | [Product Boundary Convergence](product-boundary-convergence.md) |
| How is adoption or retirement kept safe? | [Adopter Boundary And Retirement](adopter-boundary-and-retirement.md) |
| Which configuration owns a decision? | [Config Boundary Model](config-boundary-model.md) |
| When is a separate verifier appropriate? | [Independent Verification Adoption](independent-verification-adoption.md) |
| What must a Forge adapter preserve? | [Forge Provider Contract](forge-provider-contract.md) |
| What qualifies installation, signing and publication? | [Release Governance](release-governance.md) |

## Knowledge And Extensions

| Reader question | Start here |
| --- | --- |
| How should documentation be organized, expressed and linked? | [Docs Registry](docs-registry.md) |
| How do Skills guide agents without becoming authority? | [Repo-local Skills](skills.md) |
| When should an external standard replace custom machinery? | [Standards Adoption Policy](standards-adoption-policy.md) |
| How does an adapter become active or retire? | [Adapter Lifecycle](adapter-lifecycle.md) |
