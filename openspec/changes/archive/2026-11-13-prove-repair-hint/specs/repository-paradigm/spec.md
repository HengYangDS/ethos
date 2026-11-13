## ADDED Requirements

### Requirement: The paradigm routes a repairable gap to its repair

When `ethos lane repair-paradigm` would edit a carrier for any reported paradigm gap, the paradigm
report's next action, and so that of a proof, landing or publication refused only for paradigm
gaps, SHALL be the repair preview `ethos lane repair-paradigm --json`. Otherwise it SHALL be the
repair's first follow-up command, else the first gap's canonical repair. Each gap SHALL keep its
canonical repair.

#### Scenario: A repairable gap names the repair preview

- **WHEN** the only paradigm gap is a missing `.editorconfig`
- **THEN** the paradigm report's next action is `ethos lane repair-paradigm --json`
- **AND** the gap keeps its canonical repair

#### Scenario: A gap that needs judgment names its own repair

- **WHEN** the only paradigm gap is an `__init__.py` without a docstring
- **THEN** the paradigm report's next action is that gap's canonical repair
