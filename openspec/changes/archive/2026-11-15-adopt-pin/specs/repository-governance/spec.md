## MODIFIED Requirements

### Requirement: Minimal Adoption Binding

ETHOS SHALL own one typed profile binding and compose official OpenSpec configuration initialization
and readiness. A release build SHALL also plan its own exact GitHub pin and
`locked_verify_provenance` in `.config/mise/config.toml`, adding lines and replacing none; any other
build SHALL plan no pin. Optional domain, documentation, Skills and provider surfaces SHALL retain
their own owners.

#### Scenario: A repository is adopted

- **WHEN** authorized exact-HEAD adoption targets an eligible Git repository
- **THEN** it plans the ETHOS profile and the selected native OpenSpec configuration
- **AND** no placeholder, generic project context, artifact rules or unrelated surface is invented

#### Scenario: Default binding serializes from the typed contract

- **WHEN** ETHOS compiles its default profile binding
- **THEN** one strict frozen declaration validates the in-memory value and native TOML serialization
- **AND** no profile registry, renderer manifest, digest snapshot or template environment becomes a
  second owner

#### Scenario: Existing bootstrap content differs

- **WHEN** an ETHOS binding is invalid, symlinked, non-regular or unreadable
- **THEN** adoption refuses the exact path without an implicit merge, alias or migration
- **AND** a valid existing profile is preserved, while an empty ETHOS profile may be replaced
- **AND** an empty native OpenSpec configuration remains an invalid existing carrier rather than
  absent configuration

#### Scenario: Unselected optional capabilities do not block a new adopter

- **WHEN** a valid adopter has not selected optional documentation, Skills, schemas, generated
  assets or hosted providers
- **THEN** their absence does not become a bootstrap gap
- **AND** native configuration and applicable material-scope correctness remain independently
  enforced

#### Scenario: Configuration is absent

- **WHEN** adoption initializes native configuration
- **THEN** its bytes match the official initializer's default configuration
- **AND** a first Change is usable through the official CLI without generated directory anchors

#### Scenario: Native meaning cannot be preserved

- **WHEN** configuration fields, schema resolution, rule applicability or required templates fail
  native validation
- **THEN** adoption blocks before writing and retains native warnings and reasons
- **AND** unavailable supply or observation remains UNKNOWN rather than malformed-user-content blame
- **AND** a pointer-only external store receives an explicit unsupported-operation reason,
  independent of host registration

#### Scenario: Authored configuration and custom schemas already exist

- **WHEN** the official reader selects valid YAML or YML and resolves repository-owned schema inputs
- **THEN** their exact bytes remain unchanged
- **AND** an explicit expected-plan digest rejects changed configuration, schemas or templates
  before apply

#### Scenario: A file effect fails

- **WHEN** an admitted write or its native postcondition fails
- **THEN** every independently safe owned write is compensated without overwriting intervening
  content
- **AND** incomplete or unobserved recovery is not reported as successful adoption
- **AND** the initiating failure and each failed compensation remain observable
- **AND** no multi-file crash-atomic guarantee is inferred from individual atomic replacements

#### Scenario: A release build plans its own pin

- **WHEN** a release build previews the adoption of a repository whose Mise configuration is absent
  or names no ETHOS pin
- **THEN** the plan holds one step for `.config/mise/config.toml` whose diff adds the release's bare
  entry under `[tools]` and `locked_verify_provenance = true` under `[settings]`
- **AND** applying the plan changes no other line of that file
- **AND** the plan digest binds the step

#### Scenario: The exact pin is already declared

- **WHEN** the Mise configuration already holds the release's bare entry and the setting
- **THEN** the step keeps the file as it is

#### Scenario: The Mise configuration selects another ETHOS

- **WHEN** the Mise configuration names another version or another form of the pin, holds an
  `http:ethos` table, sets the provenance setting to another value or does not parse
- **THEN** the plan reports `adoption_conflict` for `.config/mise/config.toml`
- **AND** adoption writes no binding and leaves that file unchanged

#### Scenario: A development build adopts

- **WHEN** the invoking build is a development build
- **THEN** the plan holds no step for the Mise configuration
- **AND** the result says that it plans no pin
- **AND** the formation of a new repository plans no pin either
