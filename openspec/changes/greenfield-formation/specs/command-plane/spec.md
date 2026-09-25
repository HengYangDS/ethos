## ADDED Requirements

### Requirement: Formation is an explicit adoption request

The existing `ethos adopt` command SHALL expose a distinct `--create` request
for an absent target. CLI, SDK and MCP SHALL consume one typed formation result;
the default existing-repository adoption contract SHALL remain unchanged.

#### Scenario: A caller previews a new repository

- **WHEN** a caller selects `--create`, a target, a starter and a project purpose
- **THEN** the result reports exact candidate inputs, paths, hashes, conflicts and one review action
- **AND** no target repository or Git ref is created by preview.

#### Scenario: A caller requests creation

- **WHEN** an exact preview is applied with authorization and its plan digest
- **THEN** all transports invoke the same formation owner and return the same verdict, gaps and continuation
- **AND** no Agent-specific command or presentation parser grants effect authority.

#### Scenario: A caller omits creation

- **WHEN** `ethos adopt` is used without `--create` on an existing repository
- **THEN** it retains exact-HEAD-bound minimal adoption and does not write a project scaffold.
