## MODIFIED Requirements

### Requirement: Source-bound Work Lane runner bootstrap

ETHOS SHALL return a runner bootstrap for a newly started Work Lane that uses
the repository-selected immutable Git-common package runtime. The bootstrap
SHALL remain source-independent and SHALL NOT assume that the adopter checkout
or its project lock exposes an `ethos` executable.

#### Scenario: An adopter Work Lane uses its selected package runtime

- **GIVEN** the repository has a valid selected immutable runtime
- **WHEN** `ethos lane start` returns the Work Lane bootstrap
- **THEN** the command invokes that runtime's Python with `-B -I -m ethos.cli`
- **AND** it targets the new Work Lane root explicitly
- **AND** it does not create a checkout `.venv` or execute `uv run ... ethos`.

#### Scenario: a Work Lane uses its bootstrap runner

- **WHEN** the operator runs the returned runner from the linked Work Lane
- **THEN** the selected package-only runtime executes against that exact
  Work Lane root
- **AND** no checkout-local environment or adopter dependency lock is required
  to provide the ETHOS entrypoint.

#### Scenario: No selected runtime is available

- **WHEN** ETHOS cannot resolve a valid selected immutable runtime before
  starting the lane
- **THEN** lane creation fails closed before creating the ref, Lease, or
  worktree
- **AND** the result reports the exact runtime-selection gap.

### Requirement: Official Change bootstrap is a bounded write authority

An owned Work Lane with a valid current Lease SHALL be able to create and
complete exactly one official OpenSpec Change before its transient Commitment
exists. Bootstrap authority SHALL derive only from the official active Change
identifier and artifact graph, and SHALL cover only artifact paths under that
exact Change root. A request naming an exact absent Change root SHALL be
recognized as bootstrap intent but SHALL NOT grant directory-wide mutation
authority.

#### Scenario: Official metadata starts the first Change

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no other active official Change exists
- **WHEN** the official OpenSpec command creates one valid Change metadata file
- **THEN** prewrite admits that Change's official proposal, specs, design,
  tasks, and metadata paths
- **AND** no product path, unrelated Change, archive path, or generated carrier
  is admitted.

#### Scenario: Exact absent Change root resolves to metadata bootstrap

- **GIVEN** a clean owned Work Lane has a valid current Lease
- **AND** no active official Change exists
- **WHEN** prewrite receives exactly `openspec/changes/<change>` for an absent,
  valid Change identifier
- **THEN** it returns a structured block rather than directory write authority
- **AND** its unique next action is the exact prewrite command for
  `openspec/changes/<change>/.openspec.yaml`
- **AND** it does not select archived Change authority.

#### Scenario: Ordinary Commitment attribution replaces bootstrap

- **WHEN** the official Change becomes complete enough to compile its transient
  Commitment
- **THEN** current resolution uses ordinary Commitment and fresh-path
  attribution
- **AND** bootstrap authority grants no additional scope or durable permission.

#### Scenario: Ambiguous or invalid bootstrap fails closed

- **WHEN** several active Change identifiers are observed, an identifier is
  invalid, or a requested path is outside the official artifact graph
- **THEN** prewrite reports the first exact OpenSpec or uncovered-path gap
- **AND** historical archive authority, another Change, or a fallback path does
  not authorize the write.
