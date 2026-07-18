## ADDED Requirements

### Requirement: Current product HEAD external-adopter observation is bounded and durable

ETHOS SHALL be able to preserve a local, provider-neutral observation at a
current product revision against an isolated clone of an existing adopter. The
record SHALL bind product and adopter revisions, raw-bundle digest, overlay
outcome, command-parity result, and explicit non-authority boundaries.

#### Scenario: Existing adopter surfaces reject generic replacement

- **WHEN** generic overlay adoption encounters pre-existing adopter-owned ETHOS
  profile, skills, or control surfaces
- **THEN** the observation SHALL record the fail-closed conflict outcome
- **AND** it SHALL NOT state that the generic overlay replaced those surfaces
- **AND** the source adopter checkout SHALL remain unchanged.

#### Scenario: Native and external command surfaces are compared

- **WHEN** an isolated adopter clone exposes a repository-native ETHOS command
  surface and the current product runtime can address the clone
- **THEN** the record SHALL bind the two revisions and the shared command count
- **AND** it SHALL record the semantic-difference and false-negative outcomes
- **AND** it SHALL NOT claim semantic correctness, hosted-provider execution,
  remote publication, authority, or independent review from that comparison.

#### Scenario: Current observation is promoted without private coupling

- **WHEN** the local raw bundle is promoted into product evidence
- **THEN** the tracked claim and Chronicle SHALL omit workstation paths,
  adopter-private identity, credentials, keys, accounts, and provider-local
  configuration
- **AND** the claim SHALL bind a SHA-256 digest for the host-local raw bundle
- **AND** it SHALL state that remote publication was not performed.
