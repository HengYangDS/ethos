## MODIFIED Requirements

### Requirement: Semantic Lane Lifecycle Groups

ETHOS SHALL group Lease, handoff, retirement, and archive transitions under the
single `ethos lane` command family. Official Change creation and artifact
completion SHALL remain owned by the OpenSpec command plane; ETHOS SHALL NOT
advertise a parallel Change-authoring command or intent carrier.

#### Scenario: Lane lifecycle commands are grouped

- **WHEN** maintainers inspect `ethos lane --help`
- **THEN** linked retirement is exposed by `ethos lane retire landed` and
  `ethos lane retire superseded`
- **AND** exact absorbed unbound-ref retirement is exposed only by
  `ethos lane retire absorbed-ref`
- **AND** Lease lifecycle, handoff, and archive remain under
  `ethos lane lease`, `ethos lane handoff`, and `ethos lane archive-change`
- **AND** official Change creation and artifact completion remain owned by the
  OpenSpec command plane

#### Scenario: A Work Lane has no active Change

- **WHEN** current resolution observes an owned Work Lane with no active official Change
- **THEN** the single next action is the exact official `openspec new change <id>` command when the identifier is supplied by the caller
- **AND** ETHOS does not synthesize proposal, spec, design, task, scope, lineage, or Commitment files

#### Scenario: An active Change is incomplete

- **WHEN** the selected official Change reports its next ready artifact
- **THEN** the single next action names the corresponding official OpenSpec instructions command
- **AND** the machine gap preserves the exact incomplete artifact boundary
