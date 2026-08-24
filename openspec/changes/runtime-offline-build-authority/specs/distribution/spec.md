## MODIFIED Requirements

### Requirement: Source runtime uses the locked closure

ETHOS SHALL treat `uv.lock` as the dependency-resolution authority, the active
lock-current source environment as bootstrap supply, the Git-common immutable
runtime as the minimal production projection, and uv cache state as disposable.
Before using the active environment for a non-isolated source build, ETHOS SHALL
verify that environment against the lock. It SHALL then prune a copied runtime
to the hash-bound production closure and install the exact source-built ETHOS
wheel. Validation failure SHALL precede runtime selection or hook activation.

#### Scenario: Empty cache with a lock-current source environment

- **WHEN** source-checkout hook installation runs offline with an empty uv cache
  and the active environment matches `uv.lock`
- **THEN** ETHOS builds the wheel from that verified environment
- **AND** installs a runtime containing the locked production closure and exact
  ETHOS wheel without network or cache dependence.

#### Scenario: Active source environment drift

- **WHEN** the active source environment does not match `uv.lock`
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution, ambient cache contents,
  or an unverified interpreter.

#### Scenario: Lock unavailable

- **WHEN** the lock cannot define or verify the production closure
- **THEN** installation fails before producing or selecting a runtime or hook
  generation
- **AND** it does not fall back to network resolution or an unlocked closure.

#### Scenario: Package-only runtime materialization

- **WHEN** hook installation runs from a provenance-bound installed wheel rather
  than a source checkout
- **THEN** it continues to materialize the runtime from that package closure
- **AND** it resolves the exact wheel from the selected runtime's Git-common
  content-addressed package store
- **AND** it does not require uv, a source environment, a repository lock, or a
  still-existing predecessor repository path.

#### Scenario: Package-only wheel provenance is incomplete

- **WHEN** the selected runtime's content-addressed wheel is missing, ambiguous,
  or does not match its manifest digest
- **THEN** successor materialization fails before runtime or hook activation
- **AND** it does not fall back to a stale `direct_url.json`, PATH package, cache,
  or network source.
