## MODIFIED Requirements

### Requirement: Source runtime uses the locked closure

ETHOS SHALL treat `uv.lock` as the dependency-resolution authority, the exact
target source checkout's root lock-current `.venv` as build and dependency-byte
supply, the Git-common immutable runtime as the minimal production projection,
and uv cache state as disposable. Before using that environment for a
non-isolated source build, ETHOS SHALL verify its complete locked build closure.
It SHALL export only the no-development production closure, prune a copied
runtime to that hash-bound closure, install the exact source-built ETHOS wheel,
and preserve the installed distribution's unique public console-script
entrypoints in the resulting image. Validation failure SHALL precede runtime
selection or hook activation.

#### Scenario: Empty cache with a lock-current source environment

- **WHEN** source-checkout hook installation runs offline with an empty uv cache
  and the target checkout root `.venv` matches the complete `uv.lock` closure
- **THEN** ETHOS builds the wheel through that verified environment
- **AND** installs a runtime containing the locked production closure and exact
  ETHOS wheel without network or cache dependence.

#### Scenario: Active source environment drift

- **WHEN** the target checkout root `.venv` does not match `uv.lock`, including
  the build backend and locked uv package
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution, ambient cache contents,
  or an unverified interpreter.

#### Scenario: Older runtime activates newer source

- **GIVEN** the selected immutable runtime predates the target source build
  backend or dependency closure
- **WHEN** it coordinates activation for that exact source checkout
- **THEN** the target checkout root `.venv` supplies locked uv, the build
  backend, the complete build closure, and installed dependency bytes
- **AND** the selected runtime is not required to contain or emulate the newer
  source closure.

#### Scenario: Lock unavailable

- **WHEN** the lock cannot define or verify the build and production closures
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution or an unlocked closure.

#### Scenario: Package-only runtime materialization

- **WHEN** hook installation runs from a provenance-bound installed wheel rather
  than a source checkout
- **THEN** it continues to materialize the runtime from that package closure
- **AND** it resolves the exact wheel from the selected runtime's Git-common
  content-addressed package store
- **AND** it discovers the unique `ethos` console entrypoint from the installed
  wheel metadata on every supported host
- **AND** it does not require uv, a source environment, a repository lock, a
  host-specific launcher fallback, or a still-existing predecessor repository
  path.

#### Scenario: Package-only wheel provenance is incomplete

- **WHEN** the selected runtime's content-addressed wheel is missing, ambiguous,
  or does not match its manifest digest
- **THEN** successor materialization fails before runtime or hook activation
- **AND** it does not fall back to a stale `direct_url.json`, PATH package, cache,
  or network source.
