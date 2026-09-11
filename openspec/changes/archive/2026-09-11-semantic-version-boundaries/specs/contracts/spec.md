## REMOVED Requirements

### Requirement: Provider-neutral Skill Activation Contract

**Reason**: Its historical-field preservation and strict-mode variants conflict
with the supported schema and sole current skill behavior.

**Migration**: Use Skill activation preserves supported meaning. Valid current
routes and obligations remain; unsupported input fails before normalization.

## ADDED Requirements

### Requirement: Skill activation preserves supported meaning

ETHOS SHALL compile supported skill activation into a provider-neutral contract
that preserves identity, ownership, operation, lifecycle, routing, composition,
package and proof obligations. Original input SHALL be validated before
normalization; unsupported versions and fields SHALL NOT be silently discarded.

#### Scenario: Supported activation preserves meaning

- **WHEN** a valid current activation document is compiled
- **THEN** declared skill identity, routes, package and proof obligations remain explicit
- **AND** the projection carries no historical compatibility fields or single-valued mode

#### Scenario: Unsupported input is rejected before interpretation

- **WHEN** an activation document has an unsupported version or undeclared fields
- **THEN** skill validation reports the native input boundary as invalid
- **AND** normalization does not convert that input into a passing current record

#### Scenario: Required ownership is missing

- **WHEN** an active primary skill lacks required ownership or operational fields
- **THEN** the skill portfolio reports deterministic required gaps
- **AND** no compliance score can compensate for a missing obligation

### Requirement: Versions distinguish necessary interpretation boundaries

ETHOS SHALL give capabilities stable semantic names. A version discriminator
SHALL exist only where required for independent interpretation, compatibility,
migration or evidence identity. Package-local metadata and diagnostic labels
SHALL NOT add manual revision state when exact source identity already suffices.

#### Scenario: Only one capability behavior exists

- **WHEN** a mode or name only repeats an implementation generation
- **THEN** the semantic owner exposes one behavior without that label or alias
- **AND** callers consume the same owner and explicit verdict

#### Scenario: Persisted or external formats differ

- **WHEN** a version determines how an independently produced carrier is interpreted
- **THEN** the owning reader rejects unsupported input before deriving behavior
- **AND** existing signed or content-addressed evidence is not rewritten

## MODIFIED Requirements

### Requirement: Skill Package Manifest

ETHOS SHALL bind provider-visible skill packages to content-addressed package
manifests that declare entrypoint, included files, required sections, digest
algorithm, quality rules, and capability classes.

#### Scenario: package digest mismatch is detected

- **GIVEN** a skill package manifest declares included files and an expected digest
- **WHEN** package contents no longer match that digest
- **THEN** `ethos prove --gate skills --json` reports a required package digest gap

#### Scenario: unsafe package paths are rejected

- **GIVEN** a package manifest path, entrypoint, or included file escapes its allowed root
- **WHEN** ETHOS validates the manifest
- **THEN** validation reports a required package path gap without reading outside the package

#### Scenario: package capabilities are classified

- **GIVEN** a manifest declares command, MCP, script or host capabilities
- **WHEN** ETHOS validates the manifest
- **THEN** readonly capabilities reject mutations, proof capabilities identify proof commands
- **AND** guarded mutation capabilities declare a guard
