## ADDED Requirements

### Requirement: Each gate's efficacy is proven by marked tests

A test that proves a gate's behaviour SHALL declare the gate and its role with the registered
`gate` marker. A marked test SHALL NOT pass by being skipped or xfailed. A ledger of credited
(gate, role) pairs SHALL only grow, and on a whole-suite run each credited pair SHALL be covered
by a passing marked test.

#### Scenario: A marked test is skipped

- **WHEN** a test marked with `gate` skips or xfails
- **THEN** the run reports it as failed

#### Scenario: A credited proof disappears

- **WHEN** a whole-suite run collects no passing test marked for a credited (gate, role) pair
- **THEN** the efficacy test fails, naming the pair

#### Scenario: A mark names an unknown gate

- **WHEN** a test is marked with a gate id that no registry declares
- **THEN** the test fails at setup
