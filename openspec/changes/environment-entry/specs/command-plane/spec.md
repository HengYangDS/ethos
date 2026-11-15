## ADDED Requirements

### Requirement: The actor is the executor's own identity

Every catalog command SHALL accept `--actor <identity>`, except a command that hands its words to
a child command, which SHALL pass that flag on unread. A given actor SHALL take precedence over
the inherited `ETHOS_ACTOR` for every reader of the invocation and every child process it starts,
and SHALL NOT outlive the invocation.

#### Scenario: A given actor wins over the environment

- **GIVEN** a Work Lane whose Lease one actor holds, and `ETHOS_ACTOR` naming another
- **WHEN** `status` runs with `--actor` naming the holder
- **THEN** the result reports neither a missing actor nor a different holder
- **AND** a child process of the invocation observes the same actor

#### Scenario: The actor ends with its invocation

- **WHEN** an invocation with `--actor` returns or fails
- **THEN** the inherited `ETHOS_ACTOR`, or its absence, is restored
- **AND** a blank `--actor` leaves the inherited actor in place

#### Scenario: A passed-through command keeps its own flag

- **WHEN** `ethos host run` receives `--actor` among the words of its command, after `--` or
  without it
- **THEN** the child command receives the flag and its value unchanged
- **AND** the run's own actor is the inherited one

### Requirement: A missing or foreign actor continues to its own step

A result that lacks an actor SHALL continue to an `instruction` whose `inputs` name the actor's
flag. A result whose actor is not the holder of a valid Lease SHALL continue to the handoff preview
as a decision. No continuation SHALL name the holder as the actor.

#### Scenario: A missing actor is asked for

- **WHEN** `status`, `plan`, `prove`, `lane prewrite`, `hook admit` or a linked retirement runs
  where the Lease has a holder and the invocation names no actor
- **THEN** the first gap is `invocation_actor_missing` with the lane's branch
- **AND** `next` is an `instruction` with the text
  `rerun the command with --actor <your own identity>`, which names the CLI flag
- **AND** its `inputs` hold one entry, with the name `actor`, the flag `--actor` and a description

#### Scenario: A tool projection reads the same entry

- **WHEN** the operation behind the MCP `status` tool returns a result that lacks an actor
- **THEN** its `next.inputs` hold the same entry of name, flag and description

#### Scenario: A foreign actor is offered the handoff

- **WHEN** the current authority or a linked retirement finds a valid Lease whose holder is not
  the invocation's actor
- **THEN** `next` is a `decision` whose argv is the `ethos lane handoff transfer` preview, with
  the Lease's generation, expiry, branch and holder, the actor as the target and the lane as the
  root
- **AND** running that argv reports whether that generation can move

#### Scenario: A missing Lease still continues to its acquisition

- **WHEN** the current authority finds no valid Lease and the invocation names an actor
- **THEN** the next step is the `ethos lane lease reacquire` preview for that actor, as before

## MODIFIED Requirements

### Requirement: A next step names the values that only the agent chooses

A result's `next` MAY carry `inputs`: one entry for each value that only the agent can choose, with
its `name`, its `flag` and its `description`, each a string. `inputs` SHALL be absent when it is
empty. Every reader SHALL accept it and expose it unchanged, and it SHALL grant nothing. A producer
SHALL name only a flag that selects no operation. The reader of a new `next` member SHALL ship one
release before the first producer of that member.

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

#### Scenario: The first producer names the actor

- **WHEN** a command of the release after the first reader returns a result that lacks an actor
- **THEN** its `next` carries one input, whose flag is `--actor`
- **AND** no request of the catalog has a field of that name, so the flag selects no operation
- **AND** the reader of the release before reads that result and keeps the input
