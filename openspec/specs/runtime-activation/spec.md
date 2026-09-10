# runtime-activation Specification

## Purpose
Define atomic activation of immutable ETHOS runtimes, hooks, configuration,
and Git-common Lease state so upgrades either become mutually readable or
leave the prior installation unchanged.

## Requirements

### Requirement: Runtime activation includes Git-common state

ETHOS SHALL treat runtime selection, hook configuration, and the Git-common
Lease schema as one activation transition. A successful installation SHALL
leave all three mutually readable; a failed installation SHALL restore their
exact prior state.

#### Scenario: Exact legacy Lease state is migrated

- **GIVEN** the previous canonical Lease table and internally consistent rows
- **WHEN** hook installation activates a new runtime
- **THEN** each row preserves only lane, holder, generation, and expiry
- **AND** the new runtime can execute `ethos status --json` immediately.

#### Scenario: Activation fails after state migration is staged

- **WHEN** selector or hook configuration activation fails
- **THEN** the SQLite transaction rolls back
- **AND** selector bytes, Git configuration, database bytes, and sidecar absence equal their pre-state.

### Requirement: Incompatible state has one public recovery

ETHOS SHALL block before activation when legacy state cannot be projected
without ambiguity and SHALL provide one explicit authorized reset command.

#### Scenario: Legacy row is malformed or contradictory

- **WHEN** redundant legacy columns and payload disagree or required terminal values are invalid
- **THEN** installation performs no selector, hook configuration, or state effect
- **AND** status and install report `ethos hook install --reset-state --authorize --json` as the sole next action.

#### Scenario: Reset is authorized

- **WHEN** the operator executes the exact authorized reset command
- **THEN** only the obsolete Lease relation is replaced by the empty terminal relation inside the activation transaction
- **AND** existing Git refs and worktrees remain untouched and observable as unbound.

### Requirement: Locked closure self-heals before activation

Each exact locked closure SHALL be prepared once by its native owner. uv.lock
SHALL own dependency selection; the exact source root's lock-current .venv SHALL
supply build backend, locked uv and dependency bytes. Selected runtime SHALL only
coordinate activation. Before construction, check the complete exact lock,
including build tools, and export hashed non-dev production requirements.

#### Scenario: Cache fill fails

- **WHEN** a persistent uv cache is absent, read-only, or otherwise cannot be filled
- **THEN** activation performs no cache-fill effect and uses only the target
  checkout's lock-current environment
- **AND** if that environment is missing, adds, or changes a required locked
  build or production dependency, activation fails with the captured
  locked-tool diagnostic before wheel or generation construction
- **AND** selector, hook configuration, and SQLite state remain unchanged.

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

### Requirement: Native image supply is capability admitted

A congruent capability-admitted interpreter SHALL supply only the native image.
Observe the reported base first, not as authority. A directly invoked admissible
interpreter MAY supply both external roles for package-only activation. Ownership
passes to the copied, pruned, sealed, content-addressed runtime only after manifest
and native-prefix post-observation succeeds.

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

### Requirement: Installed dependency bytes have one projection owner

Source and target Python SHALL agree on ABI, version, implementation and
architecture. The supply owner SHALL project only observed regular distribution
files inside the source prefix, rejecting aliases, symlinks, escapes and hash
drift; strictly sync offline with required hashes; then install the exact ETHOS
wheel without dependencies. Runtime materialization and package acceptance SHALL
share this owner.

#### Scenario: A locked artifact is absent from cache

- **WHEN** an exact locked artifact is absent from every persistent uv cache but
  already installed in the target checkout's lock-current environment
- **THEN** ETHOS exports one hashed production requirements closure through that
  environment
- **AND** projects its observed installed distribution bytes into the congruent
  generated image
- **AND** strictly prunes the target offline before installing the exact ETHOS
  wheel without dependencies.

#### Scenario: Dependency supply is invalid or incompatible

- **WHEN** an observed dependency file is symlinked, outside the source prefix,
  changes hash before projection, aliases the target, or the two Python
  identities differ
- **THEN** the dependency-supply owner rejects the projection
- **AND** the enclosing transaction publishes no runtime, selector, hook, state,
  or acceptance receipt.

### Requirement: Runtime image preserves native execution identity

Construction SHALL preserve standalone native layout and compare paths by native
identity so the generated executable reports its image as sys.prefix and
sys.base_prefix. Authenticated Python with -B -I -m ethos.cli SHALL be the sole
internal ETHOS execution authority. Generated console scripts SHALL NOT define
runtime identity, currentness or internal execution.

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

### Requirement: Runtime discovery uses locked offline native tooling

Construction SHALL NOT install Python, access networks, require uv-managed
provenance or persistent caches. Use <supply-python> -B -I -m uv, never a guessed
sibling binary. Only if the base lacks image capability MAY this boundary list
installed candidates, with downloads, network, cache writes and project config
disabled. Selection SHALL be deterministic by identity and image capability.

#### Scenario: An incapable base triggers bounded discovery

- **WHEN** the reported base cannot supply a native image
- **THEN** discovery invokes locked uv through supply Python and lists only installed candidates
- **AND** no network, download, cache-write or project-configuration effect is enabled
- **AND** the same identity and image-capability checks determine selection.

### Requirement: Callers provision runtime supply before activation

Caller provisioning SHALL establish the source root .venv and at least one
installed discoverable native-image candidate before activation. Hosted CI SHALL
use provider-native setup. Every environment SHALL use the same resolver
observation/admission contract; provider configuration SHALL NOT bypass or alter
product semantics.

#### Scenario: Hosted conformance prepares image supply before activation

- **WHEN** a hosted host-conformance runner does not already expose an admitted
  direct Python for the requested matrix identity
- **THEN** its toolchain owner provisions that exact native image into a bounded
  job-owned installation root before synchronizing the target environment
- **AND** activation only discovers, observes, and admits the installed candidate
- **AND** a provider image whose direct Python already passes the same admission
  contract performs no redundant interpreter installation.

### Requirement: Source packages consume prepared OpenSpec supply

Source packaging SHALL consume the prepared OpenSpec production closure selected
by exact package-lock.json, without npm invocation, network access or dependence
on ambient npm caches.

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

### Requirement: Runtime cleanup uses native host process authority

Runtime activation SHALL observe active consumers through a host-native process
executable selected independently of ambient `PATH`. On Windows, required
Windows PowerShell execution SHALL resolve from the operating-system root and
SHALL NOT fall back to a same-named executable discovered on `PATH`.

#### Scenario: Package-only Windows PATH contains only Git

- **WHEN** hook installation runs from an isolated wheel with `PATH` narrowed
  to the directory containing Git
- **THEN** active-process observation invokes the absolute native Windows
  PowerShell executable under `SYSTEMROOT`
- **AND** runtime cleanup admission does not depend on ambient PowerShell
  discovery.

#### Scenario: Native Windows PowerShell is unavailable

- **WHEN** `SYSTEMROOT` is absent or its declared Windows PowerShell executable
  is not a file
- **THEN** runtime activation fails closed before deleting any generation
- **AND** the diagnostic identifies the missing native executable authority
  without trying ambient `PATH`.
