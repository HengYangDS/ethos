## ADDED Requirements

### Requirement: A next step names the values that only the agent chooses

A result's `next` MAY carry `inputs`: one entry for each value that only the agent can choose, with
the request field's `name`, its `flag` and its `description`, each a string. `inputs` SHALL be
absent when it is empty. Every reader SHALL accept it and expose it unchanged, and it SHALL grant
nothing. The reader of a new `next` member SHALL ship one release before the first producer of that
member.

#### Scenario: A reader keeps the inputs that a step carries

- **WHEN** a reader validates a result whose `next` carries `inputs`
- **THEN** the result that it exposes carries the same entries in the same order
- **AND** the step's kind, argv, effects, destructiveness and authorization are the reader's own
  derivation, whatever the carried step says

#### Scenario: A step without a value to choose keeps its bytes

- **WHEN** a result's next step has no value for the agent to choose
- **THEN** `next` has no `inputs` member
- **AND** the result serializes as it did before readers accepted the member

#### Scenario: A malformed entry refuses the payload

- **WHEN** an entry of a carried `inputs` lacks one of the three members, adds another or holds a
  value that is not a string
- **THEN** the reader refuses the payload

#### Scenario: No command emits inputs in the release that first reads them

- **WHEN** any command of the first release whose readers accept `inputs` returns a result
- **THEN** its `next` carries no `inputs`

## MODIFIED Requirements

### Requirement: The structured next step derives from the exact rendered argv

ETHOS SHALL derive `next` only from the exact ETHOS argv that `next_action` renders, by a lossless
split and join, and SHALL take its effects, authorization and destructiveness only from the catalog
operation that argv selects; an argv that selects none SHALL be `opaque` and destructive and need a
person. Prose or a template SHALL stay an instruction without an argv. Every reader SHALL re-derive
`next`, keep only the `inputs` of a carried one and check the rest only for shape.

#### Scenario: A rendered command becomes a structured step

- **WHEN** a result's `next_action` is one exact ETHOS argv
- **THEN** `next` carries that argv, its effects, its authorization and the values its flags bind

#### Scenario: Prose stays an instruction

- **WHEN** a result's `next_action` is prose, a template with a placeholder, or another tool's
  command
- **THEN** `next` is an `instruction` with no argv

#### Scenario: A reader never trusts a carried step

- **WHEN** a reader validates a payload whose `next` differs from its own derivation
- **THEN** it keeps its own derivation and the carried `inputs`, and refuses the payload only when
  the carried `next` is malformed

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

#### Scenario: Any other argv selects no operation

- **WHEN** `next_action` is a `lane`, `hook`, `attestation` or `host` argv whose path or flags
  select no catalog operation, or an ETHOS argv whose words name no catalog command, such as a
  retired command
- **THEN** `next` reports the `opaque` effect, `destructive` true, authorization `human` and an
  empty `form`

#### Scenario: Hook admission keeps its readers

- **WHEN** hook admission classifies an ETHOS argv
- **THEN** only `status` and `plan` without a mutating token are read-only, whatever `next` reports
  for the same argv
