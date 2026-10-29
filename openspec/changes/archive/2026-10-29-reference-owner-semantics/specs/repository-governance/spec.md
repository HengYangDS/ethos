## ADDED Requirements

### Requirement: Command identities come from authored command declarations

A command identity SHALL come only from a name the repository authors in a native command
declaration. A Cyclopts App names a command only through its literal `name`, and its commands
contribute identities only under a fully named path. A Python variable name, a non-literal name
and a decorator that no named Cyclopts App owns SHALL declare nothing. A single bare word in prose
SHALL be a term, not an invocation.

#### Scenario: An application variable is not a command

- **GIVEN** `app = cyclopts.App(name=PUBLIC_COMMAND)` and a document that names the MySQL user `app`
- **WHEN** prewrite admits a patch to that document
- **THEN** no command or executable `app` is observed
- **AND** a literally named App keeps its exact command identities

#### Scenario: No name is known above a command

- **WHEN** a named App is registered under an App without a static name, or a `.command`
  decorator belongs to another framework
- **THEN** neither contributes a command identity, at the root or elsewhere

#### Scenario: A function names its command as Cyclopts does

- **WHEN** a command function declares no literal name
- **THEN** its command name is Cyclopts' default transform of the function name

### Requirement: The repository's own tree owns its first-party modules

Python import ownership SHALL treat a package-relative import as internal to its package and a
module the repository provides at its root or under a leading `src/` directory as first-party. A
governed repository SHALL own the product's import package through its binding, as it owns the
product's scripts. No literal module list SHALL substitute for these relations.

#### Scenario: A relative import stays inside its package

- **WHEN** a module runs `from ._access.policy import load` or `from .subprocess import run`
- **THEN** no top-level import `_access` and no standard-library sink is observed

#### Scenario: The repository provides the module

- **WHEN** tests import `web_ingestion` from `src/web_ingestion`, or a script imports a sibling
  module under `src/`
- **THEN** the import is owned by the repository
- **AND** an import that neither the tree nor a declared distribution provides is still refused

### Requirement: Installed environment metadata maps only declared distributions

Prewrite SHALL map a declared distribution to the modules it provides from the installed metadata
of the environments that native managers place in the repository: the root `.venv` and each pixi
environment under `.pixi/envs`. It SHALL read them at each admission. An installed distribution
that the baseline does not declare SHALL own nothing.

#### Scenario: A pixi environment provides a declared distribution's module

- **GIVEN** a baseline that declares `pyyaml` and a pixi environment that installs it
- **WHEN** a patch adds `import yaml`
- **THEN** prewrite admits the import
- **AND** an installed distribution that the baseline does not declare admits nothing

### Requirement: Patch admission reports every refused reference

Patch admission SHALL report every product reference of a patch that its baseline does not own,
in stable order, so that one admission names every declaration the repository lacks.

#### Scenario: A patch consumes two unowned references

- **WHEN** a patch adds two references that no baseline owner admits
- **THEN** the admission names both refusals
- **AND** the first one remains its reason
