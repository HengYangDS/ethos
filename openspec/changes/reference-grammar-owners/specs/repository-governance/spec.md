## ADDED Requirements

### Requirement: Shell references follow POSIX nesting

Shell reference observation SHALL follow POSIX quoting and nesting. Single-quoted text SHALL be
opaque, and a command substitution, backtick command or arithmetic expansion SHALL nest with its
own quoting, also inside double quotes. Words of an arithmetic expansion SHALL be values, and a
command substitution inside it SHALL still be read. A command word that an expansion forms SHALL
name no executable, and an executable identity SHALL contain a letter or digit.

#### Scenario: Quotes inside a substitution pair within it

- **WHEN** a script runs `v="$("${python}" -c "print(str(1))")"`
- **THEN** neither `print` nor `str` is observed as an executable
- **AND** `git` in `x="$(git rev-parse HEAD)"` is observed

#### Scenario: Arithmetic is not a command

- **WHEN** a script runs `attempt=$((attempt + 1))`
- **THEN** no executable `attempt` is observed
- **AND** `wc` in `n=$(( $(wc -l < f) + 1 ))` is observed

#### Scenario: An expansion names no executable

- **WHEN** a script runs `$PYTHON -m pip install wheel`
- **THEN** no executable is observed

### Requirement: Documentation metasyntax is not a command

In a documentation carrier, a `<name>` placeholder SHALL be a value, and no word after a
placeholder in command position SHALL become a command. A `|`-joined run of words after a long
option SHALL be one value. Executed scripts SHALL keep POSIX semantics.

#### Scenario: A placeholder fills an assignment

- **WHEN** a guide shows `CODEX_HOME=<active-codex-home> codex doctor --json`
- **THEN** `codex` is observed and `doctor` is not

#### Scenario: A synopsis lists option values

- **WHEN** a reference shows `web-ingest --mode static|browser|crawl`
- **THEN** neither `browser` nor `crawl` is observed
- **AND** `ps aux|grep python` still observes `ps` and `grep`

### Requirement: A toolchain declaration owns the executable it names

Each tool that the repository's Mise configuration declares SHALL own one executable on every
platform, installed or not: its `rename_exe` when declared, otherwise the last segment of its tool
identity. A companion executable that the tool installs SHALL remain unowned unless the repository
declares it.

#### Scenario: A declared tool is invoked

- **GIVEN** a Mise configuration that declares `aqua:cue-lang/cue`
- **WHEN** a patch's script runs `cue vet`
- **THEN** prewrite admits `cue`
- **AND** `rustup` stays refused when only `rust` is declared

### Requirement: Adopter proofs report the semantic closure

An adopter's proof SHALL compute the repository's semantic reference closure and report each latent
gap with its carrier beside the audit reports, without changing the proof verdict. Blocking on those
gaps SHALL require a later Change that names the release.

#### Scenario: A latent gap is reported

- **GIVEN** an adopter carrier that references an identity its baseline does not own
- **WHEN** the adopter's full proof runs without touching that carrier
- **THEN** the proof result lists the gap with its carrier
- **AND** the proof verdict is unchanged

## MODIFIED Requirements

### Requirement: The repository's own tree owns its first-party modules

Python import ownership SHALL treat a package-relative import as internal to its package and a
module the repository provides at its root or under a leading `src/` directory as first-party.
Each top-level package, the directory directly below its nearest ancestor without `__init__.py`,
SHALL also be first-party. A governed repository SHALL own the product's import package through
its binding, as it owns the product's scripts. No literal module list SHALL substitute for these
relations.

#### Scenario: A relative import stays inside its package

- **WHEN** a module runs `from ._access.policy import load` or `from .subprocess import run`
- **THEN** no top-level import `_access` and no standard-library sink is observed

#### Scenario: The repository provides the module

- **WHEN** tests import `web_ingestion` from `src/web_ingestion`, or a script imports a sibling
  module under `src/`
- **THEN** the import is owned by the repository
- **AND** an import that neither the tree nor a declared distribution provides is still refused

#### Scenario: A hook script imports its sibling package

- **WHEN** `.githooks/pre-commit` imports `_hook` from `.githooks/_hook/`, and `.githooks/` has no
  `__init__.py`
- **THEN** the import is owned by the repository
- **AND** `model` from a standalone `examples/demo/src/model.py` is still refused

### Requirement: CI runner and retained-step records own their commands

`.config/ci/runners.toml` MAY name, per Forge, the executables and references
that the Forge's CI runner provides beyond the repository toolchain and the
product runtime. Reference admission SHALL count them as owned only in that
Forge's own pipeline files, and a malformed record SHALL own nothing. A CI step
that the retention record keeps SHALL be owned by that record as a whole, so
admission reads no command names from it until its text changes.

#### Scenario: A runner executable is used by another Forge

- **GIVEN** `.config/ci/runners.toml` names `sha256sum` for `gitlab`
- **WHEN** only `.gitlab-ci.yml` invokes `sha256sum`
- **THEN** reference closure reports no orphan consumer for `sha256sum`
- **AND** once a GitHub workflow also invokes it, `sha256sum` is reported as an
  orphan consumer.

#### Scenario: A retained PowerShell step is owned as a whole

- **GIVEN** a retention record that keeps a PowerShell `before_script` step by file, job and digest
- **WHEN** a patch touches that pipeline without changing the step
- **THEN** admission reads no command names from the step
- **AND** once the step's text changes, admission reads it again
