# Release Rules

Purpose: define release and version-bump discipline.

| Field | Rule |
| --- | --- |
| Authority | [Release Governance](../docs/governance/release-governance.md), [Terminal Governance Product Design](../docs/plans/terminal-governance-product-design.md) |
| Trigger | Version bump, changelog update, tag plan, distribution change, or publish readiness claim. |
| Action | Update all declared version and release carriers through the release workflow. |
| Evidence | Release evidence manifest, docs-code consistency checks, SBOM or attestation when in scope. |
| Stop | Version, changelog, docs examples, package metadata, or release evidence disagree. |

## Rules

- Release is a governed workflow, not a shell alias.
- Version carriers must be updated from one declared release configuration.
- Distribution adapters remain thin and must not duplicate product semantics.
- Publish readiness must separate local readiness from remote publication.
- Remote Git object publication must use the exact locally created and signed
  commit or annotated tag, a command-derived immutable request, and live
  peer-local exact CAS. Transport credentials never create, rewrite, or sign
  product objects. Partial peer effects must be reported rather than described
  as cross-peer atomicity.
