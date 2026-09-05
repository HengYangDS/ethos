## MODIFIED Requirements

### Requirement: Locked closure self-heals before activation

ETHOS SHALL prepare each exact locked dependency closure once at its native
owner boundary. `uv.lock` SHALL own dependency selection. For an exact source
checkout, its root lock-current `.venv` SHALL supply the build backend, execute
the locked uv module, and supply the selected installed dependency bytes; the
already selected runtime SHALL only coordinate activation. One congruent,
capability-admitted interpreter SHALL supply only the native Python image. The
reported base executable SHALL be the first candidate, not an authority. A
directly invoked admissible interpreter MAY own both external input roles for
package-only activation. The copied, pruned, sealed, content-addressed
generation becomes the ETHOS-owned runtime only after post-observation proves
its manifest and native prefix identity.

Before constructing a source generation, runtime materialization SHALL check
the target checkout environment against the complete exact lock, including
build tooling, and export one hashed no-development production requirements
closure. The dependency-supply owner SHALL require source and target Python
observations to agree on ABI, version, implementation, and architecture;
project only observed regular distribution files contained by the source
prefix; reject aliases, symlinks, escaped paths, and hash drift; then strictly
synchronize the target offline with required hashes and install the exact ETHOS
wheel without dependencies. Runtime materialization and package acceptance
SHALL consume this one owner.

Runtime construction SHALL NOT install another Python, access the network, or
treat uv-managed provenance or a persistent uv cache as a prerequisite. It
SHALL preserve the platform-native standalone interpreter layout and compare
observed Python paths by platform-native identity so the selected Python
executable identifies the generated image as both `sys.prefix` and
`sys.base_prefix`. The runtime's sole internal ETHOS execution authority SHALL
be that authenticated Python executable invoking `-B -I -m ethos.cli`;
generated console scripts are package projections and SHALL NOT define runtime
identity, currentness, or internal ETHOS execution. Runtime materialization
SHALL invoke the locked `uv` package as `<supply-python> -B -I -m uv`, leaving
platform-native binary discovery to that package instead of deriving a sibling
executable path. Only when the reported base lacks image capability MAY ETHOS
use that command boundary to enumerate already-installed candidates with
downloads, network access, cache writes, and project configuration disabled;
ETHOS SHALL deterministically select by its own identity and image-capability
checks.

The caller's toolchain provisioning boundary SHALL establish the target source
root `.venv` and at least one installed, discoverable native-image candidate
before activation. Hosted CI SHALL project these prerequisites through
provider-native setup. The runtime resolver SHALL apply the same observation
and admission contract in every environment; provider configuration SHALL NOT
bypass or alter product semantics.

Source package construction SHALL consume the repository-prepared OpenSpec
production closure selected by the exact `package-lock.json` without invoking
npm, accessing the network, or depending on an ambient npm cache.

#### Scenario: A virtual environment selects a native image source

- **WHEN** hook activation builds an exact source checkout whose root `.venv`
  is lock-current
- **THEN** ETHOS observes that environment's exact base executable and base
  prefix as the first image candidate
- **AND** it admits a candidate only when ABI, version, implementation,
  architecture, direct-prefix relation, and native image capability agree
- **AND** it retains the target environment as the distinct build and
  dependency-byte supply
- **AND** if the base is not admissible, it enumerates only already-installed
  candidates and performs no Python installation effect.

#### Scenario: An admissible independent interpreter is invoked directly

- **WHEN** package-only activation uses a Python that reports equal prefix and
  base prefix, its executable belongs to that prefix, and its native layout is
  copyable
- **THEN** ETHOS uses that exact executable as the runtime image source
- **AND** it performs no candidate-discovery command
- **AND** ownership remains with the source until the copied generation passes
  sealing and post-observation.

#### Scenario: No installed interpreter has image capability

- **WHEN** the observed base and every enumerated installed candidate is absent,
  virtual, identity-incongruent, outside its own prefix, or not a copyable
  native image
- **THEN** activation fails before runtime, selector, hook, or state mutation
- **AND** no package-manager command downloads or installs a replacement Python.

#### Scenario: Hosted conformance prepares image supply before activation

- **WHEN** a hosted host-conformance runner does not already expose an admitted
  direct Python for the requested matrix identity
- **THEN** its toolchain owner provisions that exact native image into a bounded
  job-owned installation root before synchronizing the target environment
- **AND** activation only discovers, observes, and admits the installed candidate
- **AND** a provider image whose direct Python already passes the same admission
  contract performs no redundant interpreter installation.

#### Scenario: A locked artifact is absent from cache

- **WHEN** an exact locked artifact is absent from every persistent uv cache but
  already installed in the target checkout's lock-current environment
- **THEN** ETHOS exports one hashed production requirements closure through that
  environment
- **AND** projects its observed installed distribution bytes into the congruent
  generated image
- **AND** strictly prunes the target offline before installing the exact ETHOS
  wheel without dependencies.

#### Scenario: Cache fill fails

- **WHEN** a persistent uv cache is absent, read-only, or otherwise cannot be filled
- **THEN** activation performs no cache-fill effect and uses only the target
  checkout's lock-current environment
- **AND** if that environment is missing, adds, or changes a required locked
  build or production dependency, activation fails with the captured
  locked-tool diagnostic before wheel or generation construction
- **AND** selector, hook configuration, and SQLite state remain unchanged.

#### Scenario: Dependency supply is invalid or incompatible

- **WHEN** an observed dependency file is symlinked, outside the source prefix,
  changes hash before projection, aliases the target, or the two Python
  identities differ
- **THEN** the dependency-supply owner rejects the projection
- **AND** the enclosing transaction publishes no runtime, selector, hook, state,
  or acceptance receipt.

#### Scenario: Offline preflight passes

- **WHEN** the target checkout environment passes the complete locked offline
  check and hashed production requirements export
- **THEN** runtime construction projects and strictly synchronizes that same
  production closure offline
- **AND** no cache path contributes to runtime correctness or identity.

#### Scenario: An older runtime coordinates a newer source build

- **GIVEN** the invoking selected runtime does not contain the target source
  checkout's build backend or current locked dependency versions
- **WHEN** activation selects that exact checkout as the runtime build source
- **THEN** all build and dependency-supply commands execute through the target
  checkout's verified root `.venv`
- **AND** the invoking runtime contributes no target dependency or build bytes.

#### Scenario: A selected package runtime supplies its successor

- **WHEN** activation is invoked from the currently selected immutable package
  runtime without an exact source checkout
- **THEN** ETHOS reuses that validated production closure and exact
  content-addressed wheel
- **AND** successor construction requires no source checkout, dependency cache,
  or network access.

#### Scenario: A Windows standalone interpreter is materialized

- **WHEN** runtime activation copies an admitted Windows CPython image source
- **THEN** `python.exe`, `Lib`, `DLLs`, and native runtime DLLs retain their
  platform-relative layout
- **AND** executing the copy reports a path-identical generated image root as
  both `sys.prefix` and `sys.base_prefix`, regardless of equivalent Windows
  separator or case spelling
- **AND** runtime post-observation and selected-runtime continuations execute
  `python.exe -B -I -m ethos.cli`
- **AND** relocating the generation does not depend on `Scripts/ethos.exe`.

#### Scenario: Runtime module execution fails

- **WHEN** the authenticated runtime Python cannot execute `ethos.cli`
- **THEN** activation fails before selector mutation
- **AND** evidence identifies the exact command, return code, stdout, and stderr.

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
- **AND** wheel construction requires neither registry access nor npm cache state.
