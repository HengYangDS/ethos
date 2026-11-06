# runtime-activation Specification

## Purpose

Define atomic activation of immutable ETHOS runtimes, hooks, configuration,
and Git-common Lease state so upgrades either become mutually readable or
leave the prior installation unchanged.

## Requirements

### Requirement: Runtime activation includes Git-common state

ETHOS SHALL treat runtime selection, hook configuration and the Git-common
Lease schema as one activation transition. Successful activation SHALL leave
all three mutually readable; failed activation SHALL restore their exact prior
state. Later reclamation SHALL preserve successful activation and report its
independent completed, retained or deferred effects.

#### Scenario: Exact legacy Lease state is migrated

- **GIVEN** the previous canonical Lease table and internally consistent rows
- **WHEN** hook installation activates a new runtime
- **THEN** each row preserves only lane, holder, generation and expiry
- **AND** the new runtime can execute `ethos status --json` immediately.

#### Scenario: Activation fails after state migration is staged

- **WHEN** selector or hook configuration activation fails
- **THEN** the SQLite transaction rolls back
- **AND** selector bytes, Git configuration, database bytes and sidecar absence equal their pre-state.

#### Scenario: Successful activation has deferred reclamation

- **WHEN** the runtime, hooks and state have activated successfully but reclamation cannot finish
- **THEN** the result preserves the successful activation observation
- **AND** it reports the precise reclamation boundary and a fresh public recovery action without undoing completed effects.

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

Construction SHALL preserve standalone native layout and compare paths by native identity so the
generated executable reports its image as sys.prefix and sys.base_prefix. Authenticated Python with
`-B -I -X utf8 -m ethos.cli` SHALL be the sole internal ETHOS execution authority, and one product
owner SHALL name those interpreter flags for every Python process ETHOS starts. Generated console
scripts SHALL NOT define runtime identity, currentness or internal execution.

#### Scenario: A Windows standalone interpreter is materialized

- **WHEN** runtime activation copies an admitted Windows CPython image source
- **THEN** `python.exe`, `Lib`, `DLLs`, and native runtime DLLs retain their platform-relative
  layout
- **AND** executing the copy reports a path-identical generated image root as both `sys.prefix` and
  `sys.base_prefix`, regardless of equivalent Windows separator or case spelling
- **AND** runtime post-observation and selected-runtime continuations execute
  `python.exe -B -I -X utf8 -m ethos.cli`
- **AND** relocating the generation does not depend on `Scripts/ethos.exe`.

#### Scenario: Runtime module execution fails

- **WHEN** the authenticated runtime Python cannot execute `ethos.cli`
- **THEN** activation fails before selector mutation
- **AND** evidence identifies the exact command, return code, stdout, and stderr.

#### Scenario: ETHOS runs on a host whose locale is not UTF-8

- **WHEN** ETHOS starts its runtime Python, a release console launcher starts it, or ETHOS starts
  supply Python
- **THEN** that process runs in Python's UTF-8 mode
- **AND** its default file, standard-stream and pipe encoding is UTF-8.

### Requirement: Runtime discovery uses locked offline native tooling

Construction SHALL NOT install Python, access networks, require uv-managed provenance or persistent
caches. Use <supply-python> -B -I -X utf8 -m uv, never a guessed sibling binary. Only if the base
lacks image capability MAY this boundary list installed candidates, with downloads, network, cache
writes and project config disabled. Selection SHALL be deterministic by identity and image
capability.

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

Runtime activation SHALL observe active consumers through host-native process authority selected
independently of ambient `PATH`. On Windows, it SHALL read process command lines from the operating
system's management interface in its own process within a bound, without starting another program.

#### Scenario: Package-only Windows PATH contains only Git

- **WHEN** hook installation runs from an isolated wheel with `PATH` narrowed to the directory
  containing Git
- **THEN** active-process observation reads every visible process's command line, including its own,
  without starting a child process
- **AND** runtime cleanup admission does not depend on ambient program discovery.

#### Scenario: Native Windows PowerShell is unavailable

- **WHEN** `SYSTEMROOT` is absent or its Windows PowerShell executable is not a file
- **THEN** active-process observation reads command lines through the management interface without
  that executable
- **AND** runtime activation does not try ambient `PATH`.

#### Scenario: Native Windows process observation is unavailable

- **WHEN** the management query fails or does not complete within its bound
- **THEN** runtime activation fails closed with `hook_runtime_consumers_unknown` before deleting any
  generation
- **AND** does not try ambient `PATH`.

### Requirement: Installation records the configuration it replaces

When `ethos hook install` replaces a value that ETHOS does not own, it SHALL record that value, per key, in the common and worktree scopes, and an absent value as absent. It SHALL NOT record a value that ETHOS owns, current or legacy, SHALL keep the recorded entry of a key it already owns, and SHALL write the record and clear an earlier exit's receipt within the activation, restoring both if the activation fails.

#### Scenario: A repository with its own hooks adopts ETHOS

- **GIVEN** a repository whose `core.hooksPath` names its own hooks directory
- **WHEN** `ethos hook install` activates a runtime
- **THEN** the record names that hooks path
- **AND** a later upgrade leaves the record unchanged.

#### Scenario: A repository without a hooks path adopts ETHOS

- **WHEN** `ethos hook install` activates a runtime in a repository without `core.hooksPath`
- **THEN** the record holds the hooks path as absent.

#### Scenario: A legacy ETHOS hooks path is replaced

- **WHEN** install replaces a worktree's `core.hooksPath` that names a legacy ETHOS hooks directory
- **THEN** the record holds no entry for that value.

#### Scenario: A repository adopts ETHOS again

- **GIVEN** a repository whose hooks path changed after an earlier adoption or exit
- **WHEN** `ethos hook install` activates a runtime
- **THEN** the record names the new hooks path
- **AND** no earlier exit receipt remains.

### Requirement: A repository exit is previewed before any effect

`ethos adopt --exit` SHALL report, without any effect, the configuration after the exit per key, the keys it keeps because ETHOS no longer owns them, the keys it leaves unrecorded, the record entries it cannot restore, the generations it removes and keeps, the selectors with their hashes, the Leases and unlanded branches, and a digest over them. It SHALL resume an interrupted exit from its receipt.

#### Scenario: An exit is inspected

- **WHEN** `ethos adopt --exit --json` runs in an adopted repository with a recorded configuration
- **THEN** it reports the configuration after the exit, the selector hashes and a plan digest
- **AND** no file, configuration or selector changes.

#### Scenario: A key changed after adoption

- **WHEN** a hooks path set after adoption no longer names ETHOS's hooks
- **THEN** the preview keeps it and reports it as kept.

#### Scenario: A repository is not adopted

- **WHEN** the repository has no runtime selector, no hooks path that ETHOS owns and no
  interrupted exit
- **THEN** the exit reports `adoption_exit_not_adopted` and plans no effect
- **AND** it reads no hand-made file as a record.

#### Scenario: An exit was interrupted

- **WHEN** an exit's receipt is still applying
- **THEN** the preview plans the remaining steps from that receipt.

#### Scenario: No configuration was recorded

- **WHEN** the repository was adopted before installation recorded its configuration
- **AND** its hooks path is still ETHOS's
- **THEN** the exit's next action names the Git commands that settle the hooks path.

#### Scenario: A lane holds a live Lease

- **WHEN** a Work Lane of the repository holds a valid Lease
- **THEN** the exit preview names that Lease as a blocker
- **AND** its plan digest differs from one made before the Lease.

#### Scenario: A running process uses the runtime

- **WHEN** a process other than the exit's own refers to the repository's runtime or hooks
  generations
- **THEN** the exit preview names `adoption_exit_runtime_in_use` as a blocker.

### Requirement: A previewed exit is applied in a fenced order

With `--apply`, `--authorize`, the current head and the previewed digest, the exit SHALL, under the runtime selection lock and a state write transaction, write a durable receipt, remove the record, restore each key that still holds ETHOS's value, verify that no worktree uses ETHOS's hooks, remove each selector that still holds its planned bytes, and mark the receipt applied. A failure SHALL attempt every compensation step and report any that fails.

#### Scenario: An adopted repository exits

- **GIVEN** a repository with its own hooks path that adopted ETHOS
- **WHEN** the exit is applied with the previewed digest
- **THEN** the hooks path is its own again and no selector remains
- **AND** the receipt holds the selector hashes and the configuration before and after.

#### Scenario: The plan changed after the preview

- **WHEN** a key, a selector or a blocker changes between the preview and the apply
- **THEN** the exit is refused and nothing changes.

#### Scenario: An exit fails after restoring the configuration

- **WHEN** a step after the receipt fails
- **THEN** every compensation step is attempted
- **AND** the result is `unknown` when one of them fails.

### Requirement: Status reports an exit

Status SHALL report an applied exit while no runtime is selected, and an interrupted exit whenever its receipt remains, and a repository without a repository profile SHALL NOT require hooks once it has exited.

#### Scenario: Status after an exit

- **WHEN** status runs in a repository that exited
- **THEN** it reports the exit and its receipt.

#### Scenario: Status after an interrupted exit

- **WHEN** an exit stopped before it marked its receipt applied
- **THEN** status reports the exit as incomplete.

### Requirement: An exit names its blockers and decisions

The exit SHALL name as a blocker a valid or unknown Lease, a held selection lock or proof slot, and a running process other than its own that refers to the runtime or hooks generations or to an installed runtime a selector names, and SHALL treat a process it cannot read as unknown. Without a record it SHALL ask, while a hooks path ETHOS owns remains, for the exact decision on that path.

#### Scenario: The exit's own process

- **WHEN** only the exit's own process refers to the repository's runtime
- **THEN** the exit preview names no running process as a blocker.

#### Scenario: A process cannot be read

- **WHEN** a running process's command line cannot be read
- **THEN** the exit preview names `adoption_exit_runtime_use_unknown` as a blocker.

### Requirement: A rollback across a repaired declaration refuses until restored

Hook activation SHALL probe the target runtime against the root's tree before it pins anything,
whenever `--runtime` names a build other than the invoking one. When the target refuses the tree's
publication declaration, activation SHALL refuse with `runtime_rollback_declaration_repaired` and
leave no effect. The refusal SHALL name restoring the predecessor's declaration in a lane as the
next action.

#### Scenario: A selector-only rollback after the repair

- **WHEN** an operator activates the ROLLBACK runtime on a tree whose declaration the repair changed
- **THEN** activation refuses with `runtime_rollback_declaration_repaired`
- **AND** selectors, hooks and state are unchanged

#### Scenario: A rollback after the restore

- **WHEN** a lane restores the predecessor's declaration and its HEAD contains the accepted tip
- **THEN** activating ROLLBACK on that lane succeeds

### Requirement: Status names the supported rollback

While a ROLLBACK runtime is held, status SHALL name the one supported rollback: the CURRENT runtime
activating it for the root, which reaches the declaration preflight.

#### Scenario: A cutover holds the predecessor

- **WHEN** a cutover holds the predecessor as ROLLBACK
- **THEN** status names the CURRENT runtime's `hook install --root <root> --runtime <ROLLBACK>`
