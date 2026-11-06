## ADDED Requirements

### Requirement: Readers of another ETHOS process read its result in full

An ETHOS operation that runs another ETHOS process and reads its JSON result SHALL first expand a
bounded result through its digest-bound detail before it reads any field that the bound may move or
shorten. Expansion SHALL return the result as its producer wrote it.

#### Scenario: A bounded predecessor result is read in full

- **WHEN** landing's predecessor policy probe receives a bounded result from the installed runtime
- **THEN** it reads the proof plan and the gaps from the detail that the bound names
- **AND** a detail that is missing or disagrees with the bound blocks with
  `predecessor_policy_probe_invalid`

#### Scenario: Another build's result stays readable

- **WHEN** the detail holds a result that the reader's own result model would refuse
- **THEN** expansion still returns it, bound by its digest, its size and every field the bound
  keeps
- **AND** a reader that needs its own model validates the expanded result itself
