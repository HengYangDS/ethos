## ADDED Requirements

### Requirement: Container environment declarations own runtime values

The common reference owner SHALL read the names that a tracked Dockerfile or Containerfile declares with `ENV` or `ARG`, and the environment of each Compose service, as declared runtime values. A container build's own commands run against its image and SHALL NOT become repository executable consumers.

#### Scenario: A Dockerfile declares a value

- **GIVEN** a tracked Dockerfile declares `ENV GATE=1`, `ARG GATE` or the legacy `ENV GATE 1`
- **WHEN** maintained code reads `GATE`
- **THEN** reference closure recognizes the declaration
- **AND** a read of an undeclared value remains an orphan consumer

#### Scenario: A Compose service declares a value

- **GIVEN** a Compose service lists `GATE` in its `environment`, as a mapping or as a list
- **WHEN** maintained code reads `GATE`
- **THEN** reference closure recognizes the declaration

#### Scenario: Build commands are not consumers

- **WHEN** a Dockerfile `RUN` instruction invokes a tool
- **THEN** no repository executable consumer is observed from it

## MODIFIED Requirements

### Requirement: Python reference observation respects binding and call site

Python consumer observation SHALL resolve statically determinable executable and environment reads from import binding, lexical scope and the values that can reach the call. Parsing a carrier SHALL NOT by itself establish semantic coverage. A sink chosen by dynamic lookup SHALL make its carrier UNKNOWN, not a fabricated reference or a whole-repository block; a value supplied at run time stays with its producer. Patch admission, repository audit and private-boundary consumers share this owner.

#### Scenario: Aliases preserve a real consumer

- **WHEN** `subprocess.run`, an aliased module or imported `run` invokes an undeclared executable, or aliased `os.getenv` reads an undeclared input
- **THEN** the public repository-audit gate identifies the corresponding missing declaration
- **AND** a spelling-only rewrite does not change the observed behavior

#### Scenario: Shadowing cannot invent an effect

- **WHEN** a local object named `subprocess` has a harmless `run` method
- **THEN** no standard-library executable consumer is inferred from that call
- **AND** the otherwise valid source remains eligible

#### Scenario: The value belongs to its scope and program point

- **WHEN** a global name is shadowed locally or assigned after `getenv(NAME)`
- **THEN** the read uses only values possible at that call in its lexical scope
- **AND** a later assignment cannot erase an earlier undeclared input

#### Scenario: Dynamic semantics remain bounded unknown

- **WHEN** a sink is chosen by dynamic lookup, such as `getattr(subprocess, name)` with a computed name
- **THEN** its carrier is UNKNOWN and cannot pass as evaluated
- **AND** the carrier's statically resolved references and unrelated files retain their result

#### Scenario: A run-time value stays with its producer

- **WHEN** an executor or environment read receives a parameter or a call result
- **THEN** no reference is invented at that call and the carrier stays evaluated
- **AND** a command constant that no executor runs is not a consumer
