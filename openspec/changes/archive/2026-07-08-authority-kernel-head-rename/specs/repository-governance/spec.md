## MODIFIED Requirements

### Requirement: Protected Root Projection Pollution
Accepted roots SHALL reject host projection and scratch decomposition paths as
repository truth unless the material is deliberately promoted through a Work Lane.

#### Scenario: Root projection pollution is visible
- **WHEN** a protected root contains `CLAUDE.md`, `.claude`, `.gitnexus`, `.ethos/decomp-recipes`, or `docs/superpowers`
- **THEN** repository audit reports a design-integrity gap
- **AND** the gap classifies as untrusted substrate state
