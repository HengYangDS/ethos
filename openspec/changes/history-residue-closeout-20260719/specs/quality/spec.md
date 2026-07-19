## ADDED Requirements

### Requirement: Rules V2 migration is lossless for active policy

ETHOS SHALL expose the advertised Rules V2 migration through the public command
plane and SHALL preserve active non-legacy policy, including the complete
`[quality]` tree, while normalizing legacy rule keys.

#### Scenario: A mixed-generation rules file is migrated

- **WHEN** `ethos rules migrate` evaluates a file containing legacy rules and
  active quality, source-budget, and gate policy
- **THEN** dry-run reports the complete target without modifying the file
- **AND** authorized apply with the expected current HEAD preserves the parsed
  active policy and converts `paths`, `requires`, and `evidence` to V2 keys.

#### Scenario: Migration input is ambiguous or stale

- **WHEN** the rules file is unparsable, write admission fails, authorization is
  absent, or expected HEAD does not match
- **THEN** migration fails closed without rewriting the file.

### Requirement: Expired source-budget debt closes through measured deletion

ETHOS SHALL require expired source-budget allowances to be eliminated through
measured carrier deletion or consolidation and SHALL NOT treat a baseline reset,
silent expiry rollover, or replacement umbrella debt as settlement.

#### Scenario: A debt record has expired

- **WHEN** global source-budget closeout evaluates a record whose expiry is in
  the past
- **THEN** the report remains blocked until live inventory no longer requires the
  record's category allowances
- **AND** baseline metrics, terminal targets, inventory categories, and
  unexpired records remain unchanged.

#### Scenario: All expired allowances are eliminated

- **WHEN** measured net deletion brings every category within the baseline plus
  still-active unexpired allowances
- **THEN** the expired records and their unused waves can be removed
- **AND** `ethos quality source-budget --json` reports no expired-debt or
  exceeded-budget gap.
