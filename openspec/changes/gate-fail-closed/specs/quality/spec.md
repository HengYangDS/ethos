## ADDED Requirements

### Requirement: One gate's failure refuses only that gate

The shared runner SHALL turn any exception that one provider or one gate raises into that gate's
outcome, SHALL record the error's type, message and raising frame, and SHALL keep running every
other admitted gate. An interrupt SHALL stop the whole run.

#### Scenario: A gate raises an unexpected error

- **WHEN** one gate's execution raises `KeyError` while an independent gate is admitted
- **THEN** that gate blocks with `gate_runner_error:<gate>` and exit code 1
- **AND** its dependents report `gate_dependency_not_proven:<gate>`
- **AND** the independent gate's result is reported

#### Scenario: A provider raises an unlisted error

- **WHEN** a provider raises `KeyError`
- **THEN** its gate blocks with `gate_provider_error:<gate>:<provider>`

#### Scenario: The run is interrupted

- **WHEN** a gate's execution is interrupted
- **THEN** the interrupt stops the whole run

### Requirement: A contained failure keeps its verdict class

A contained timeout SHALL stay unknown with `gate_timeout:<gate>`. A contained error that carries a
decision SHALL keep its verdict class, with its gaps after the seam's class gap. Any other error
SHALL block with the class gap alone. A provider report that JSON cannot represent SHALL fail its
provider.

#### Scenario: A failure carries its own decision

- **WHEN** a gate raises a process failure whose verdict is unknown
- **THEN** the gate is unknown with `gate_runner_error:<gate>` and the failure's own gaps

#### Scenario: A provider report cannot be recorded

- **WHEN** a provider returns a report that holds a value JSON cannot represent
- **THEN** its gate blocks with `gate_provider_error:<gate>:<provider>`
