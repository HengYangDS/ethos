## MODIFIED Requirements

### Requirement: Authority and historical truth boundaries

ETHOS SHALL keep authority vocabulary clean across repository records while
preserving historical chronology and meaning.

#### Scenario: Repository records exclude retired authority-head vocabulary

- **WHEN** repository architecture tests inspect git-admissible repository records
- **THEN** source code, schemas, docs, rules, hooks, config, README, evidence,
  claims, and archived OpenSpec records do not expose retired authority-head
  vocabulary
- **AND** the current kernel head remains `Authority`

#### Scenario: Historical records preserve meaning without retired tokens

- **WHEN** evidence chronicles, evidence claims, or archived OpenSpec changes
  recorded earlier authority-head terminology at the time
- **THEN** ETHOS preserves the historical meaning and chronology without retaining
  retired authority-head tokens
- **AND** cleanup tests cover Chronicle and archives instead of exempting them
