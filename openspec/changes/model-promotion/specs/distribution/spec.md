## ADDED Requirements

### Requirement: Source-independent runtime identity

The wheel, entrypoint, dependency lock, OpenSpec runtime, package resources, JSON schemas, help projection, and hook launchers SHALL be bound by one immutable manifest and SHALL execute without a source checkout, staging path, user absolute path, or mutable host interpreter dependency.

#### Scenario: Final-path smoke test

- **WHEN** installation materializes a candidate runtime
- **THEN** ETHOS moves it to its final content-addressed path, runs package-only black-box commands there, atomically switches bindings only after success, and then retires legacy locators

#### Scenario: Package identity is audited

- **WHEN** an accepted runtime receipt is inspected
- **THEN** it binds source HEAD/tree/signature, wheel, entrypoint, dependency
  lock, OpenSpec 1.8 payload, schemas, help, hooks, manifest, SBOM, provenance,
  runtime digest, and readback hashes

#### Scenario: Supported Python implementations execute the package

- **WHEN** package-only conformance runs on Python 3.12, 3.13, 3.14, and later
  supported versions across declared platforms
- **THEN** the same contracts, resources, commands, hooks, and schemas pass

### Requirement: Active runtime is healthy and portable

Exactly one manifest-selected runtime SHALL be active. Launchers SHALL NOT bind
a temporary staging directory, source checkout, user-specific absolute source
path, or mutable Homebrew patch-level interpreter location.

#### Scenario: Host interpreter patch version disappears

- **WHEN** the previously used host runtime is upgraded or removed
- **THEN** runtime preflight repairs or replaces the package atomically before
  activation
- **AND** no generated hook points to the broken runtime

#### Scenario: Superseded runtimes are cleaned

- **WHEN** active manifest and every launcher read back one healthy runtime
- **THEN** a public housekeeping receipt may remove inactive broken generations
- **AND** active or still-referenced bytes remain untouched

### Requirement: Formatter-safe traceability parsing

OpenSpec requirement-to-task-to-proof tables SHALL be parsed from Markdown
structure rather than presentation whitespace. Formatter alignment SHALL NOT
change their semantic rows.

#### Scenario: Prettier aligns table cells

- **WHEN** Prettier inserts variable padding around table cell content
- **THEN** ETHOS extracts the same requirement, task, and proof edges

### Requirement: Complete hook-family convergence

ETHOS SHALL remain the sole `core.hooksPath` owner and SHALL atomically converge pre-commit, commit-msg, pre-push, and reference-transaction across the repository family to one immutable runtime. Repository-native commit policy SHALL be invoked through declared structured argv and locked inputs.

#### Scenario: Split hook generations

- **WHEN** installed hooks point to more than one runtime generation
- **THEN** hook install reports the split and either converges the complete family atomically or leaves every prior binding unchanged

#### Scenario: Repository declares no commit-message validator

- **WHEN** commit-msg installation is requested without a policy declaration
- **THEN** ETHOS reports the missing declaration without inventing a grammar,
  wrapper, personal executable, or second hooks owner
