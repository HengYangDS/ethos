## MODIFIED Requirements

### Requirement: One locked toolchain owner exposes the common verbs

A repository SHALL select its toolchain through one locked owner: `.config/mise/` with locked
resolution when it needs tools beyond its package manager, otherwise its package manager and
lockfile. That owner SHALL expose `bootstrap`, `fix` and `check` as tasks. A mise configuration that
selects no tool needs no lock, since mise writes none for it.

#### Scenario: Toolchain configuration sits at the root

- **WHEN** a repository tracks a root `mise.toml`
- **THEN** the paradigm reports its canonical path `.config/mise/config.toml`.

#### Scenario: A verb is missing

- **WHEN** the toolchain owner exposes no `fix` task
- **THEN** the paradigm reports a missing common verb.

#### Scenario: A configuration selects no tool

- **WHEN** `.config/mise/config.toml` sets `locked = true` and declares the three verbs but selects
  no tool, through `[tools]`, idiomatic version files or `.tool-versions`
- **THEN** the paradigm requires no `.config/mise/mise.lock`
- **AND** a configuration that selects a tool still requires the tracked lock.
