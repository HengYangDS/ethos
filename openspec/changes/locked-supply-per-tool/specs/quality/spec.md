## MODIFIED Requirements

### Requirement: Locked supply is complete before ETHOS uses it

Before ETHOS returns a locked tool, native mise SHALL report, in the same isolated safe-mode resolution, the declared tool named after it installed at its locked version with an existing install path, and the executable SHALL resolve inside that install path. A locked environment SHALL NOT resolve a declared tool's own executable from another tool's install path. A refusal SHALL name the missing tool or the executable outside its tool, and resolution SHALL NOT return another tool's executable in a declared tool's place.

#### Scenario: A declared tool is not installed

- **WHEN** a repository locks a tool that native mise reports as not installed at its locked version, and its executable resolves from another tool
- **THEN** a locked tool or environment for that repository is refused with `mise_supply_incomplete` naming that tool
- **AND** no executable of another tool, such as Node's bundled npm for a locked npm, is returned

#### Scenario: Another tool supplies a declared tool's executable

- **WHEN** an executable that a declared tool provides under its own name resolves inside another tool's install path
- **THEN** resolution is refused with `mise_executable_outside_tool` naming that executable

#### Scenario: A tool is provisioned on first use

- **WHEN** a declared tool is not yet installed and no other tool provides its executable
- **THEN** a locked tool of another declared tool and the locked environment still resolve

#### Scenario: A complete supply

- **WHEN** every declared tool is installed at its locked version
- **THEN** resolution returns the locked tool or environment
- **AND** an executable that no declared tool names, such as npm where only node is declared, resolves as native mise selects it
