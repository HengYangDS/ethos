## MODIFIED Requirements

### Requirement: Cyclopts And API Own Interface Semantics

The operation catalog SHALL declare every command's name, parameters, help and selection once, for
the root commands and the group commands alike; Cyclopts SHALL render them through one generic
adapter, and the in-process operation API SHALL select through the same catalog. ETHOS SHALL NOT
maintain a parallel command registry, lazy report-handler DSL, re-export facade, or command-shaped
quality plane.

#### Scenario: A command signature changes

- **WHEN** a public operation changes its parameters or help
- **THEN** CLI, SDK metadata, generated docs, and protocol projections derive from the same
  operation declaration
- **AND** a root operation's keyword signature that differs from its request model fails the catalog
  table test

#### Scenario: ETHOS runs from an installed wheel

- **WHEN** the package runs outside a source checkout
- **THEN** packaged lifecycle and gate resources remain available
- **AND** command discovery still comes from the catalog and Cyclopts declarations, not a packaged
  command registry

### Requirement: CLI Surface Delegation

The CLI SHALL compose output and UX while delegating semantics to contracts, operations, repository
policy, and adapters; one generic adapter SHALL derive every catalog command, root and group, from
the operation catalog.

#### Scenario: CLI package is scanned

- **WHEN** architecture tests inspect imports
- **THEN** command modules call concrete operation and adapter owners
- **AND** no command registry besides the operation catalog, no generic report compiler and no CLI
  subprocess loopback exists

### Requirement: The structured next step derives from the exact rendered argv

ETHOS SHALL derive `next` only from the exact ETHOS argv that `next_action` renders, by a lossless
split and join, and SHALL take its effects, authorization and destructiveness from the catalog
operation any such argv selects, root or group. Prose or a template SHALL stay an instruction
without an argv. Every reader SHALL re-derive `next` and check a carried one only for shape.

#### Scenario: A rendered command becomes a structured step

- **WHEN** a result's `next_action` is one exact ETHOS argv
- **THEN** `next` carries that argv, its effects, its authorization and the values its flags bind

#### Scenario: Prose stays an instruction

- **WHEN** a result's `next_action` is prose, a template with a placeholder, or another tool's
  command
- **THEN** `next` is an `instruction` with no argv

#### Scenario: A reader never trusts a carried step

- **WHEN** a reader validates a payload whose `next` differs from its own derivation
- **THEN** it keeps its own derivation, and refuses the payload only when the carried `next` is
  malformed

#### Scenario: A deleting argv is destructive

- **WHEN** `next_action` selects the deletion of something the command does not recreate, such as a
  retirement apply, a `publish --retire` apply, `attestation release` or a `land --retag` apply
- **THEN** `next.destructive` is true

#### Scenario: An opaque step needs a person

- **WHEN** `next_action` is `ethos host run` or `ethos mcp`, whose argv cannot bound what it runs
- **THEN** `next` reports the `opaque` effect, `destructive` true and authorization `human`

#### Scenario: A root argv selects no operation

- **WHEN** `next_action` is a root argv whose flags select no catalog operation, or set a field its
  operation does not take
- **THEN** `next` reports the `opaque` effect, `destructive` true, authorization `human` and an
  empty `form`

#### Scenario: A group argv selects no operation

- **WHEN** `next_action` is a `lane`, `hook`, `attestation` or `host` argv whose path or flags
  select no catalog operation
- **THEN** `next` reports the `opaque` effect, `destructive` true, authorization `human` and an
  empty `form`

#### Scenario: Hook admission keeps its readers

- **WHEN** hook admission classifies an ETHOS argv
- **THEN** only `status` and `plan` without a mutating token are read-only, whatever `next` reports
  for the same argv

## ADDED Requirements

### Requirement: Group commands are catalog operations

Every `lane`, `hook`, `attestation` and `host run` leaf SHALL be a catalog entry selected by its
command path and flags, with a kernel half in `ethos.contracts.operations` and an application half
in `ethos.application`; the surfaces SHALL hold no leaf body. `ethos mcp` SHALL remain a transport
launcher outside the catalog.

#### Scenario: A group request names a field its operation does not take

- **WHEN** a group leaf is run with a field outside its selected mode, such as `--authorize`
  without `--apply`
- **THEN** it runs nothing and exits 2 with `command_field_refused:<field>`
- **AND** a check that owns a body gap code, such as the retirement receipt, keeps that code

#### Scenario: A usage error names the full path

- **WHEN** a group leaf is run with a required field omitted
- **THEN** it exits 2 with `command_usage_invalid:<command path>` and a payload `command` equal to
  that path

#### Scenario: Help lists the catalog

- **WHEN** `ethos <path> --help` or `ethos <group> --help --json` is rendered
- **THEN** it prints that command's or group's part of the catalog within the declared help payload
  budget
- **AND** bare `ethos --help` lists no hidden group

#### Scenario: Host run exits with its child

- **WHEN** `ethos host run -- <command>` runs a command that the host admits
- **THEN** the entry's `process` exit makes the CLI exit with the child's status and print no frame
- **AND** an admission gap is emitted as a result like any other
