## MODIFIED Requirements

### Requirement: Source-bound Work Lane runner bootstrap

ETHOS SHALL return a runner bootstrap for a newly started Work Lane that uses the
repository-selected immutable Git-common package runtime. The bootstrap SHALL remain
source-independent and SHALL NOT assume that the adopter checkout or its project lock exposes an
`ethos` executable.

#### Scenario: An adopter Work Lane uses its selected package runtime

- **GIVEN** the repository has a valid selected immutable runtime
- **WHEN** `ethos lane start` returns the Work Lane bootstrap
- **THEN** the command invokes that runtime's Python with `-B -I -X utf8 -m ethos.cli`
- **AND** it targets the new Work Lane root explicitly
- **AND** it does not create a checkout `.venv` or execute `uv run ... ethos`.

#### Scenario: a Work Lane uses its bootstrap runner

- **WHEN** the operator runs the returned runner from the linked Work Lane
- **THEN** the selected package-only runtime executes against that exact Work Lane root
- **AND** no checkout-local environment or adopter dependency lock is required to provide the ETHOS
  entrypoint.

#### Scenario: No selected runtime is available

- **WHEN** ETHOS cannot resolve a valid selected immutable runtime before starting the lane
- **THEN** lane creation fails closed before creating the ref, Lease, or worktree
- **AND** the result reports the exact runtime-selection gap.
