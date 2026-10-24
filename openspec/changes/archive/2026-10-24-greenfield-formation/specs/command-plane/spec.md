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

#### Scenario: A caller previews starter evolution

- **WHEN** CLI, SDK or MCP selects `adopt --evolve-starter` on a formed repository
- **THEN** the same owner checks recorded starter provenance and returns a reviewable old/current/new proposal with exact changed paths or a typed refusal
- **AND** preview changes no project files or refs; `--apply` cannot use generator provenance as repository write authority.

#### Scenario: MCP binds an absent formation target

- **WHEN** an MCP host explicitly selects `mcp --create-target --root` for an absent destination
- **THEN** its adopt tool consumes the same typed formation plan as CLI and SDK, while default MCP binding still requires an existing root
- **AND** the requested root and actor remain bound across calls; parent retargeting, root overrides and an existing target cannot redirect creation.

#### Scenario: A Git root has no accepted commit

- **WHEN** status or candidate bootstrap observes an unborn accepted branch
- **THEN** it reports the missing accepted HEAD and a first-commit recovery action without creating a candidate ref or emitting a traceback.
