## MODIFIED Requirements
### Requirement: Product Boundary and Contributor Policy Gate
ETHOS SHALL keep active product surfaces, release metadata, and contributor
policy organization-native rather than person-native or adopter-private.

#### Scenario: Active product boundary is enforced
- **WHEN** hosted CI, pre-commit, local CI, or `ethos prove --execute --json`
  runs the product boundary gate
- **THEN** ETHOS invokes `tools/ci/scripts/run-product-boundary.sh`
- **AND** the owner script runs `ethos quality product-boundary --json` and
  `ethos quality contributor-policy --json`
- **AND** active product surfaces reject hardcoded personal identity literals,
  local workstation paths, private infrastructure URLs, adopter-specific
  literals, generic lifecycle bucket phrases, session-authority phrases, and
  person attribution fields in release/package metadata
- **AND** ignored host-local state under `.ethos/state/**` is not scanned as an
  active product surface
- **AND** historical evidence and archived change records may retain factual
  names only as historical records, not as active product defaults or authority
