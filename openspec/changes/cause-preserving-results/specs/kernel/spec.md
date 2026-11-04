## ADDED Requirements

### Requirement: Results compose their parts' causes

An aggregate result SHALL reduce its parts' verdicts, block before unknown before pass, and SHALL keep every part's own gaps: the part's class code first, then at most five of its cause codes, with one bounded diagnostic that counts the rest. An exception that carries a result SHALL carry all of its gaps and its verdict class, and a boundary SHALL NOT turn an unknown part into block.

#### Scenario: A gate times out during an executed proof

- **WHEN** an executed proof's gate exceeds its deadline
- **THEN** the proof's required gaps list `gate_unknown:<gate>` and then `gate_timeout:<gate>`
- **AND** the proof's verdict is unknown, with one diagnostic that names the gate, its bound and
  its elapsed seconds

#### Scenario: A refusal finds several gaps

- **WHEN** a command refuses because of several gaps
- **THEN** its result lists every one of them, not only the first

#### Scenario: A part reports many causes

- **WHEN** a part reports more than five cause codes
- **THEN** the result keeps its class code and five cause codes
- **AND** the part's diagnostic counts the omitted ones
