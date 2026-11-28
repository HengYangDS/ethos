## ADDED Requirements

### Requirement: Runtime cleanup observes consumers through the host's process lister

Runtime activation SHALL observe active consumers through the process lister that the host's default
command path holds, selected independently of ambient `PATH`, within a bound.

#### Scenario: Ambient PATH holds only Git

- **WHEN** hook installation runs from an isolated wheel with `PATH` narrowed to the directory
  containing Git
- **THEN** active-process observation runs the process lister that the host's default command path
  holds
- **AND** runtime cleanup admission does not depend on ambient program discovery.

#### Scenario: The process lister fails

- **WHEN** the host's process lister exits with a failure or writes to its error stream
- **THEN** runtime activation fails closed with `hook_runtime_consumers_unknown`
- **AND** it deletes no generation whose consumers it did not observe
- **AND** does not try ambient `PATH`.

#### Scenario: The host holds no process lister

- **WHEN** the host's default command path holds no process lister
- **THEN** process observation refuses with `native_process_observer_unavailable`
- **AND** runtime activation deletes no generation whose consumers it did not observe.

## REMOVED Requirements

### Requirement: Runtime cleanup uses native host process authority

**Reason**: Every scenario of it described the Windows management interface or Windows PowerShell,
and ETHOS supports no Windows host (owner's decision of 2026-11-25).

**Migration**: None for an adopter on macOS or Linux: the observation is unchanged. The requirement
"Runtime cleanup observes consumers through the host's process lister" states it.
