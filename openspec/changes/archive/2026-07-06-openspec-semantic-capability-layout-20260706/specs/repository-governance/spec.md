## ADDED Requirements

### Requirement: Semantic OpenSpec Capability Layout

ETHOS SHALL identify accepted OpenSpec capabilities by stable product semantics
rather than implementation package names.

#### Scenario: accepted specs use semantic capability IDs

- **WHEN** repository audit inspects `openspec/specs`
- **THEN** the required capability directories are `kernel`, `contracts`,
  `repository-governance`, `adapters`, `command-plane`,
  `assistant-projections`, `distribution`, `quality`, and `proof-hosts`
- **AND** no accepted capability directory is required merely because it mirrors
  a retired package or host surface name
- **AND** `capability.toml` records implementation ownership as metadata rather
  than capability identity

### Requirement: Test Gate Remains Owner-script Governed

ETHOS SHALL absorb parallelism and performance visibility through the reusable
test owner script rather than duplicating pytest policy in hosted CI providers.

#### Scenario: test mechanism absorption preserves CI projection boundary

- **WHEN** ETHOS hardens Python test execution
- **THEN** `.config/ci/scripts/run-python-tests.sh` remains the reusable owner
- **AND** hosted CI invokes the owner script instead of copying pytest flags
- **AND** optional benchmark and report mechanisms remain planned until admitted
  as active gates
