## MODIFIED Requirements

### Requirement: Source-bound Work Lane runner bootstrap

ETHOS SHALL return a runner bootstrap for a newly started Work Lane and SHALL
route repository-owned Python owner scripts and installed local Git hooks through
the same semantic runtime bootstrap. Python source environments MUST be under
`build/runtime/venv` in the executing checkout. uv download caching MUST have an
explicit host-or-CI cache boundary and MUST NOT require a root `.venv` or a
checkout-local opaque uv cache. The runner and hook path MUST bind to the
current checkout source rather than a sibling Work Lane or accepted-root
installation.

#### Scenario: a Work Lane uses its bootstrap runner

- **WHEN** the operator runs the returned runner from the linked Work Lane
- **THEN** the uv environment is under `build/runtime/venv` in that Work Lane
- **AND** uv cache selection is explicit at the host or CI boundary
- **AND** the command runner binds to that Work Lane source

#### Scenario: a hook runs without a root virtual environment

- **GIVEN** a repository has the ETHOS hooks installed and no root `.venv`
- **WHEN** a hook invokes the ETHOS command path
- **THEN** it resolves the checkout-bound semantic runtime bootstrap or an
  explicitly supplied interpreter
- **AND** it does not fall back to `<repo>/.venv/bin/python`
- **AND** a hook quality tool with a development dependency invokes that tool
  through the bootstrap-bound uv development group

## ADDED Requirements

### Requirement: Worktree-bound semantic runtime bootstrap

ETHOS SHALL provide one repository-owned runtime bootstrap for product Python
execution. The bootstrap MUST bind `UV_PROJECT_ENVIRONMENT` to
`build/runtime/venv` under the current Git worktree and MUST execute against
that checkout's source tree. The bootstrap SHALL expose an explicit cache
boundary: an explicitly supplied CI or operator cache location takes precedence;
otherwise uv download state uses a host-scoped content-addressed cache outside
the repository checkout. A nested bootstrap that enters a different worktree
while an outer uv invocation holds the selected cache lock MUST use a bounded
child namespace beneath that selected cache root; it MUST retain the child
worktree's source environment and MUST NOT wait on the outer lock. An owner
script launched through the explicit `ETHOS_RUNTIME_BOOTSTRAPPED=1` handoff MUST
run its outer uv command with `--no-sync`, so a tool invoked by that script does
not wait on a parent process holding the same worktree environment lock.

#### Scenario: two Work Lanes initialize independently

- **GIVEN** two linked Work Lanes from the same Git common directory
- **WHEN** each runs a Python owner command through the bootstrap
- **THEN** each command receives its own `<worktree>/build/runtime/venv`
- **AND** neither command resolves `<worktree>/.venv` as its project environment
- **AND** the cache location does not become a Work Lane lease, source, evidence,
  or authority store

#### Scenario: a hook starts before its checkout environment exists

- **GIVEN** a hook requests the default
  `<worktree>/build/runtime/venv/bin/python` and that interpreter is absent
- **WHEN** the request passes through the runtime bootstrap
- **THEN** the bootstrap invokes `uv run --group dev python` with the original
  Python arguments and lets uv materialize only that checkout's environment
- **AND** it does not resolve `<worktree>/.venv/bin/python`

#### Scenario: a nested hook bootstrap avoids parent cache-lock reentry

- **GIVEN** an outer uv command holds the selected cache lock for one worktree
- **WHEN** a Git hook in a different worktree requests its missing default
  semantic interpreter through the bootstrap
- **THEN** the hook materializes only the child worktree's
  `build/runtime/venv`
- **AND** its uv invocation uses a bounded namespace beneath the selected host
  or CI cache root
- **AND** it does not wait on or share the outer uv cache lock

#### Scenario: a marked owner script does not reenter its own environment lock

- **GIVEN** a product owner script is handed off through
  `env ETHOS_RUNTIME_BOOTSTRAPPED=1 <script>`
- **WHEN** the runtime bootstrap launches that handoff
- **THEN** its outer `uv run` invocation includes `--no-sync`
- **AND** the script retains ownership of any later tool synchronization
- **AND** an inner tool invocation does not wait on a parent process holding
  the same `<worktree>/build/runtime/venv` lock

### Requirement: Explicit execution overrides remain bounded

ETHOS SHALL permit an explicit `ETHOS_PYTHON`, `PYTHON`, `UV_CACHE_DIR`, or
`ETHOS_UV_CACHE_DIR` override for a bounded invocation. An override MUST NOT
change the checkout root, substitute another checkout's source environment, or
silently make root `.venv` the default runtime.

#### Scenario: CI supplies its own cache path

- **GIVEN** a hosted CI projection supplies an explicit uv cache location
- **WHEN** an owner script invokes the runtime bootstrap
- **THEN** the bootstrap preserves that cache location
- **AND** the source environment remains under the current checkout's
  `build/runtime/venv`

### Requirement: Generated Artifact Topology Contract

ETHOS SHALL classify generated outputs by semantic lifecycle and SHALL audit
active executable producer entrypoints as well as existing files. Root `.venv`
MUST NOT be an active normal-execution environment. Existing ignored root
`.venv` directories MAY remain as non-authoritative migration residue until an
explicit local operator removes them; ETHOS MUST NOT delete them automatically.
Host-bootstrap adapters that install a missing hosted toolchain or configure the
checkout before a repository runtime exists MAY invoke the host interpreter, but
MUST NOT execute product modules and MUST remain explicitly allowlisted by the
topology audit.

#### Scenario: an executable entrypoint attempts root environment fallback

- **WHEN** generated-artifact topology audits a product-owned executable script,
  hook, or CI projection containing an active root `.venv/bin/python` fallback
  or bare `uv run` path that bypasses the semantic bootstrap
- **THEN** the audit reports a required runtime-entrypoint routing gap
- **AND** proof remains blocked until the producer routes through the bootstrap

#### Scenario: legacy root environment remains observable but non-authoritative

- **GIVEN** an ignored root `.venv` exists after the runtime contract changes
- **WHEN** topology and local-state audits run
- **THEN** they identify it as migration residue rather than product truth
- **AND** no cleanup command removes it without an explicit local operator action

### Requirement: Recoverable generated test-evidence lock

ETHOS SHALL serialize generated Python coverage evidence writes without allowing
an interrupted writer to leave future proof waiting indefinitely. The lock MUST
record its current owner process identity: PID plus start fingerprint. A later
writer MAY reclaim a lock only when that recorded identity no longer identifies
a live process; it MUST NOT preempt an unknown or live owner, and it MUST fail
after a bounded wait with an actionable lock diagnostic. Lock metadata remains
ignored generated state rather than repository truth.

#### Scenario: a dead coverage writer lock is reclaimed safely

- **GIVEN** a generated coverage lock records a process identity with no live
  process matching its PID and start fingerprint
- **WHEN** a later owner test gate requests that same coverage evidence home
- **THEN** it removes the dead-owner marker and empty lock before acquiring it
- **AND** a live or unknown owner remains protected from preemption
- **AND** the command reports bounded failure instead of waiting forever when
  it cannot safely acquire the lock
