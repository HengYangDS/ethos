## MODIFIED Requirements

### Requirement: Platform support is established by native delivered behavior

ETHOS SHALL deliver native macOS and Linux support on explicitly declared
architecture and OS baselines. Windows support SHOULD be provided when qualified.
Required-platform delivery SHALL NOT depend on an unqualified Windows path. A host
platform MAY be served by a runtime that its operating system emulates, only after
that host qualifies those exact bytes. Runtime identity and tool supply SHALL name
the architecture that the interpreter executes, not the host CPU.

#### Scenario: A release advertises supported platforms

- **WHEN** a platform is included in the release support declaration
- **THEN** its delivered artifact passes native installation, CLI/MCP and hooks
- **AND** unsupported combinations remain explicit rather than inheriting another platform's proof

#### Scenario: An emulating host qualifies an x64 runtime

- **WHEN** the release leg that declares `windows-arm64` qualifies the x64 runtime it built
- **THEN** the release declares `windows-arm64` with the archive that leg qualified
- **AND** no wheel is published for `windows-arm64`

#### Scenario: An emulated interpreter selects its runtime

- **WHEN** an x64 interpreter that Windows on Arm emulates selects its runtime
- **THEN** the runtime's recorded architecture is `x86_64`, as its interpreter executes
- **AND** the `ARM64` CPU that the operating system reports does not refuse the selection
