## ADDED Requirements

### Requirement: Internal ETHOS Gate Fast Path
ETHOS SHALL execute internal ETHOS JSON gates in-process when safe.

#### Scenario: Internal gate runs without nested CLI process
- **WHEN** the local runner executes `python -m ethos.cli <command> --json`
- **THEN** ETHOS invokes the command plane in-process
- **AND** external provider commands still use the subprocess adapter
