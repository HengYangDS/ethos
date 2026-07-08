## MODIFIED Requirements

### Requirement: Authority and historical truth boundaries

ETHOS SHALL keep current authority vocabulary clean without rewriting historical
repository records.

#### Scenario: Current truth excludes predecessor vocabulary

- **WHEN** repository architecture tests inspect tracked current truth surfaces
- **THEN** source code, schemas, active docs, rules, hooks, config, README, and
  live OpenSpec specs do not expose the authority predecessor term
- **AND** the current kernel head remains `Authority`

#### Scenario: Historical records preserve predecessor vocabulary

- **WHEN** evidence chronicles, evidence claims, or archived OpenSpec changes
  recorded a predecessor term at the time
- **THEN** ETHOS may preserve that vocabulary as historical evidence
- **AND** current-truth cleanup tests do not require Chronicle or archives to be
  rewritten into today's vocabulary
