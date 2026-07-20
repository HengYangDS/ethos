## ADDED Requirements

### Requirement: Container contracts are opt-in, provider-neutral, and product-schema-bound

ETHOS SHALL validate a container-delivery contract only when an adopter profile
declares `[container_contract]`.  The declaration and referenced manifest SHALL
be validated with product-owned schemas and SHALL not become valid through an
adopter-local relaxed schema copy.

#### Scenario: Undeclared repository remains valid

- **WHEN** a governed repository has no container-contract declaration
- **THEN** validation reports `not_declared` without a required gap
- **AND** it does not infer that container delivery is required.

#### Scenario: Declared contract binds a contained manifest

- **WHEN** an adopter profile declares a contract manifest below its repository
  root
- **THEN** ETHOS validates the declaration and manifest with product schemas
- **AND** a missing, directory, unreadable, or root-escaping manifest produces
  a required gap.

#### Scenario: Semantic delivery evidence is fail-closed

- **WHEN** a declared manifest omits required Linux architecture smoke evidence,
  uses untracked or hash-mismatched evidence, duplicates an asset identifier,
  omits persistent restore policy, names a prohibited runtime vendor, or
  references an invalid untrusted output schema
- **THEN** validation produces a stable required gap
- **AND** schema reporting includes that gap in normal promotion readiness.

#### Scenario: Valid evidence remains provider-neutral

- **WHEN** a declared manifest contains exactly the required architecture and
  recovery evidence with matching tracked digests
- **THEN** validation is valid
- **AND** it makes no hosted-CI, image-publication, or local-runtime success
  claim.
