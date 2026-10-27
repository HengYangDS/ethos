## MODIFIED Requirements

### Requirement: Provider-neutral Contracts

ETHOS SHALL keep JSON schemas, TOML config contracts, public result contracts,
attestation envelopes, and evidence contracts free of provider-specific
execution behavior.

#### Scenario: Contracts are inspected

- **WHEN** imports of modules under `src/ethos/contracts` are inspected
- **THEN** contract modules do not import Git, SQLite, subprocess, hosted CI,
  assistant runtime, or adopter-private implementation modules

### Requirement: Governed Repository Context Contract

ETHOS SHALL define a governed repository context contract for every repository
subject. This is the shared governance context contract for repository audit,
proof and command payloads.

#### Scenario: Governance context is provider-neutral

- **WHEN** ETHOS emits `governance_context`
- **THEN** `contract` is `governed_repository` and `truth_boundary` is
  `repository`
- **AND** the context records `profile`, `profile_boundary`, and digest-bound
  `agent_guidance` sources
- **AND** `reader_projection_commands` contains `ethos status`
- **AND** provider, host, editor, model, and toolchain choices remain outside
  product semantics

### Requirement: Documentation carrier contract

ETHOS SHALL distinguish human-facing Markdown, durable TOML config, public JSON
command output, ecosystem-native YAML, generated JSONL, ignored local indexes,
and Git-set Attestations by author, lifecycle, and truth status.

#### Scenario: Machine and human carriers do not collapse

- **WHEN** ETHOS defines a repository governance record
- **THEN** durable hand-authored configuration uses TOML unless an ecosystem
  standard requires another carrier
- **AND** public command and MCP payloads use JSON
- **AND** human judgment, design, reviews, and retrospectives use Markdown

### Requirement: Handoff Package Contract

ETHOS SHALL define digest-bound handoff packages as context projections over
repository truth.

#### Scenario: Handoff package is validated

- **WHEN** a handoff package is inspected
- **THEN** it records the source lane ref, head and tree, target holder ref, context and dirty-content digests, source Lease binding, and digest-bound artifacts
- **AND** stale source digests block trust-bearing handoff claims
- **AND** handoff content remains context until recorded as an Attestation

### Requirement: Declarative Registry Compilation

ETHOS SHALL compile durable `system/` declarations, including the gate registry,
from strict frozen TOML contracts before emitting public projections.

#### Scenario: A valid declaration projects stable registry data

- **WHEN** a registry declaration is loaded
- **THEN** its contract validates before projection
- **AND** declared static fields preserve order and payload shape
- **AND** runtime facts are added only at adapter boundaries

#### Scenario: An invalid declaration is rejected before projection

- **WHEN** a declaration contains unknown fields, duplicate ids, or malformed admission data
- **THEN** no partial public registry is emitted
- **AND** declaration-level tests cover the rejection

## REMOVED Requirements

### Requirement: Trust Envelope Contract

**Reason**: Its claim fields were removed in `3d393c93a`, and the kernel admits no Claim mode.

**Migration**: Trust is carried by Attestation v2 and the proof trust boundary (DR-0006).

### Requirement: Promotion Target Contract

**Reason**: `promotion_target` was removed in `3d393c93a`.

**Migration**: None; no current carrier has a promotion target.

### Requirement: Capability Profile Contract

**Reason**: Capability profiles were removed with `openspec/specs/*/capability.toml` in `3d393c93a`, and `openspec/specs/README.md` admits no parallel routing metadata.

**Migration**: Capability meaning stays in the accepted specs.

### Requirement: Capability Profile Facet Contract

**Reason**: Its recommended facets and decision axes were removed in `3d393c93a`.

**Migration**: Capability meaning stays in the accepted specs.
