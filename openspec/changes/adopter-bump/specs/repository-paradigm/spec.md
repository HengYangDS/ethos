## ADDED Requirements

### Requirement: The paradigm repair declares the ETHOS selection on request

With `--pin`, `ethos lane repair-paradigm` SHALL plan first, in the same admitted patch as its
other repairs, the bare entry of the release that runs it as the ETHOS selection in
`.config/mise/config.toml`: it replaces an older bare pin or the `http:ethos` table and adds a
first pin. It SHALL block a tree that selects a newer release. After an apply that wrote the
selection the next action SHALL be `mise --cd <root> lock`. Without `--pin` the command SHALL read
no selection.

#### Scenario: An older bare pin is moved

- **WHEN** the configuration holds the bare pin of an older release and a release runs the
  command with `--pin`
- **THEN** the preview shows the pin line of the invoking release and writes nothing
- **AND** the apply writes that line and `locked_verify_provenance = true`, keeps every other key
  and names `mise --cd <root> lock` as the next action

#### Scenario: The older table is replaced

- **WHEN** the configuration holds the `http:ethos` table of the same or an older release
- **THEN** the plan removes the table with its sub-tables and adds the release's bare entry
- **AND** every other key of the configuration keeps its value

#### Scenario: A tree without a selection gets its first pin

- **WHEN** the configuration holds no ETHOS entry, or the tree holds no Mise configuration
- **THEN** the plan adds the release's bare entry, creating the configuration where none exists
- **AND** a second preview plans no edit and names no step

#### Scenario: The move shares one admitted patch with another repair

- **WHEN** the plan also repairs the common OpenSpec rules of the repository
- **THEN** the apply asks one prewrite admission that names both carriers, and writes both

#### Scenario: The apply names the projection step after the relock

- **WHEN** the repository tracks a projection declaration and an apply wrote the selection
- **THEN** the result's actions name `mise --cd <root> lock` and then
  `ethos lane project --root <root> --json`
- **AND** ETHOS runs neither

#### Scenario: A repeated upgrade plans nothing

- **WHEN** the command runs again with `--pin` on the written configuration
- **THEN** it plans no edit and names no step

#### Scenario: A newer selection blocks the request

- **WHEN** the configuration selects a release newer than the invoking one, in either form
- **THEN** the preview and the apply block with `runtime_pin_ahead:<version>` and plan no edit of
  any carrier
- **AND** the next action is
  `mise --cd <root> exec --locked -- ethos lane repair-paradigm --pin --root <root> --json`
- **AND** the same tree's plan without `--pin` is what it was

#### Scenario: Another selection stays reported

- **WHEN** the configuration holds both forms or a pin with options
- **THEN** the result reports `runtime-pin` with its repair and plans no edit of the configuration

#### Scenario: A development build names no target

- **WHEN** a development build runs the command with `--pin` on an older bare pin
- **THEN** the result reports `runtime-pin` and plans no edit of the configuration

#### Scenario: The selection is read only on request

- **WHEN** the command runs without `--pin` on a conforming repository that holds no pin
- **THEN** the result is conforming and names no step

#### Scenario: Adoption's conflict names the move

- **WHEN** a release's adoption refuses a Mise configuration that holds an older bare pin or the
  `http:ethos` table of the same or an older release
- **THEN** the conflict's next action names
  `ethos lane repair-paradigm --pin --root <root> --json` and says that it runs in a Work Lane
- **AND** a conflict for a newer selection or a pin with options does not name it
