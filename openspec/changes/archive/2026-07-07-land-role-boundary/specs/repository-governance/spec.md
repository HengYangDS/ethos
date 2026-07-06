# repository-governance Delta

## MODIFIED Requirements

### Requirement: Land readiness respects branch-role boundaries

`ethos land --json` MUST report readiness only for Work Lane to candidate
promotion. Protected roots MUST use the accepted-root closeout path.

#### Scenario: Work Lane dry-run land remains read-only readiness

- **WHEN** a clean Work Lane runs `ethos land --json`
- **THEN** ETHOS evaluates repository audit and candidate-base readiness without
  requiring authorization, expect-head, or executed proof side effects

#### Scenario: Accepted root normal land is blocked

- **WHEN** an accepted-root checkout runs `ethos land --json` without `--closeout`
- **THEN** ETHOS reports `protected_root_mutation`
- **AND** the next action is `ethos land --closeout --json`

#### Scenario: Candidate normal land is blocked

- **WHEN** a candidate checkout runs `ethos land --json` without `--closeout`
- **THEN** ETHOS reports `protected_root_mutation`
- **AND** the next action is `ethos land --closeout --json`
