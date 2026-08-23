## REMOVED Requirements

### Requirement: Self OpenSpec Lifecycle Mode

**Reason**: The removed `ethos openspec` root duplicated official OpenSpec
inspection and the declared ETHOS proof gates.

**Migration**: Use the official OpenSpec CLI for carrier inspection and
`ethos plan` / `ethos prove` for ETHOS admission and proof.

### Requirement: ETHOS OpenSpec adapter remains under one command plane

**Reason**: A dedicated OpenSpec root was a parallel public command surface for
facts already owned by the official CLI and ETHOS proof plan.

**Migration**: Use official OpenSpec commands for carrier lifecycle and the
existing ETHOS lifecycle commands for repository effects.

### Requirement: Explain Command Projects Invalid-State Signals

**Reason**: A standalone taxonomy command duplicated the typed diagnostics and
single executable `next_action` already projected by each public command.

**Migration**: Consume the originating command's diagnostics, required gaps,
and exact next action.

### Requirement: OpenSpec archive query uses logical Change IDs

**Reason**: A standalone archive query duplicated official archive structure
and current lifecycle selection.

**Migration**: Inspect archives with the official OpenSpec CLI; execute governed
archive effects only through `ethos lane archive-change`.

### Requirement: Active Change selection excludes archive directory names

**Reason**: The retired `ethos openspec` selector no longer exists.

**Migration**: Official OpenSpec selects active carriers; ETHOS consumes the
selected Commitment and rejects non-current carrier bindings at admission.

## MODIFIED Requirements

### Requirement: Semantic Lane Lifecycle Groups

ETHOS SHALL group Lease, handoff, retirement, archive, and successor-Change
transitions under the single `ethos lane` command family.

#### Scenario: Lane lifecycle commands are grouped

- **WHEN** maintainers inspect `ethos lane --help`
- **THEN** linked retirement is exposed by `ethos lane retire landed` and
  `ethos lane retire superseded`
- **AND** exact absorbed unbound-ref retirement is exposed only by
  `ethos lane retire absorbed-ref`
- **AND** Lease lifecycle, handoff, archive, and successor creation remain under
  `ethos lane lease`, `ethos lane handoff`, `ethos lane archive-change`, and
  `ethos lane start-change` respectively
