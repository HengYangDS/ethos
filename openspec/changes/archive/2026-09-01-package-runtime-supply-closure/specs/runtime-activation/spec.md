## MODIFIED Requirements

### Requirement: Locked closure self-heals before activation

ETHOS SHALL prepare each exact locked dependency closure once at its native
owner boundary. Python runtime activation SHALL fill and prove the Git-common
hashed Python supply before selector mutation. Source package construction
SHALL consume the repository-prepared OpenSpec production closure selected by
the exact `package-lock.json` without invoking npm, accessing the network, or
depending on an ambient npm cache.

#### Scenario: A locked artifact is absent from cache

- **WHEN** an exact hashed Python artifact is absent from the Git-common cache
- **THEN** hook installation fetches it during one owned pre-activation sync
- **AND** deletes the temporary sync target
- **AND** the immutable runtime installation succeeds with network access disabled.

#### Scenario: Cache fill fails

- **WHEN** the exact hashed Python closure cannot be fetched or installed
- **THEN** hook installation fails with the captured tool diagnostic
- **AND** selector, hook configuration, and SQLite state remain unchanged.

#### Scenario: Offline preflight passes

- **WHEN** the owned Git-common cache contains every locked Python artifact
- **THEN** runtime construction reuses the same exported requirements offline
- **AND** no activation step can discover or select a different closure.

#### Scenario: A prepared OpenSpec production closure is packaged

- **WHEN** wheel or sdist construction receives a prepared `node_modules` root
  matching every non-development, non-link package in the exact source lock
- **THEN** the build includes only those production package roots
- **AND** it invokes no npm command, reads no npm cache, opens no network route,
  and creates no second dependency tree.

#### Scenario: Prepared OpenSpec supply is absent or drifted

- **WHEN** a locked production package is absent, symlinked, has a different
  package version, or contains an undeclared nested package root
- **THEN** artifact construction fails before emitting an artifact
- **AND** the result identifies the exact package path and the single native
  provisioning action `npm ci --ignore-scripts`.

#### Scenario: A wheel is built from the source distribution

- **WHEN** the sdist is the source for a later wheel build
- **THEN** its packaged OpenSpec production closure is validated against the
  same lock and reused directly
- **AND** wheel construction requires neither registry access nor npm cache
  state.
