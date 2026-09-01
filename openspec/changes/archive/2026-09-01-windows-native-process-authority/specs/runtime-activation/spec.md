## ADDED Requirements

### Requirement: Runtime cleanup uses native host process authority

Runtime activation SHALL observe active consumers through a host-native process
executable selected independently of ambient `PATH`. On Windows, required
Windows PowerShell execution SHALL resolve from the operating-system root and
SHALL NOT fall back to a same-named executable discovered on `PATH`.

#### Scenario: Package-only Windows PATH contains only Git

- **WHEN** hook installation runs from an isolated wheel with `PATH` narrowed
  to the directory containing Git
- **THEN** active-process observation invokes the absolute native Windows
  PowerShell executable under `SYSTEMROOT`
- **AND** runtime cleanup admission does not depend on ambient PowerShell
  discovery.

#### Scenario: Native Windows PowerShell is unavailable

- **WHEN** `SYSTEMROOT` is absent or its declared Windows PowerShell executable
  is not a file
- **THEN** runtime activation fails closed before deleting any generation
- **AND** the diagnostic identifies the missing native executable authority
  without trying ambient `PATH`.
