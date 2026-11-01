## MODIFIED Requirements

### Requirement: Runtime cleanup uses native host process authority

Runtime activation SHALL observe active consumers through host-native process authority selected
independently of ambient `PATH`. On Windows, it SHALL read process command lines from the operating
system's management interface in its own process within a bound, without starting another program.

#### Scenario: Package-only Windows PATH contains only Git

- **WHEN** hook installation runs from an isolated wheel with `PATH` narrowed to the directory
  containing Git
- **THEN** active-process observation reads every visible process's command line, including its own,
  without starting a child process
- **AND** runtime cleanup admission does not depend on ambient program discovery.

#### Scenario: Native Windows PowerShell is unavailable

- **WHEN** `SYSTEMROOT` is absent or its Windows PowerShell executable is not a file
- **THEN** active-process observation reads command lines through the management interface without
  that executable
- **AND** runtime activation does not try ambient `PATH`.

#### Scenario: Native Windows process observation is unavailable

- **WHEN** the management query fails or does not complete within its bound
- **THEN** runtime activation fails closed with `hook_runtime_consumers_unknown` before deleting any
  generation
- **AND** does not try ambient `PATH`.
