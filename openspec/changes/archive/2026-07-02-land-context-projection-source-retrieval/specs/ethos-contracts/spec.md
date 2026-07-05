## ADDED Requirements

### Requirement: Context Projection Contracts

ETHOS SHALL define provider-neutral contracts for assistant context bundles, selection reports, index manifests, and retrieval policy.

#### Scenario: Retrieved context remains advisory

- **WHEN** a context bundle includes retrieved repository spans
- **THEN** each span is source-verified against current repository content
- **AND** the bundle declares that retrieved context cannot satisfy proof, claims, or required gaps.
