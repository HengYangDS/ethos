## MODIFIED Requirements

### Requirement: Worktree-bound semantic runtime bootstrap

One repository bootstrap SHALL bind `UV_PROJECT_ENVIRONMENT` to the current
worktree's `build/runtime/venv` and execute that checkout's source. Explicit
cache roots win; otherwise downloads use a host-scoped content-addressed cache.
Nested cross-worktree bootstrap SHALL use a bounded child cache namespace and
keep child source without waiting on the outer lock.
`ETHOS_RUNTIME_BOOTSTRAPPED=1` owner scripts SHALL invoke outer uv with
`--no-sync`. When that marker is already set and the request names the current
worktree's executable semantic Python with a valid `pyvenv.cfg`, the bootstrap
SHALL execute the original Python request directly without `uv sync` or a
nested `uv run`; it MUST NOT require an inherited runtime root to equal the
current worktree.

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

#### Scenario: marked semantic Python bypasses nested synchronization

- **GIVEN** a hook or owner process has `ETHOS_RUNTIME_BOOTSTRAPPED=1`
- **AND** it requests the current worktree's executable
  `build/runtime/venv/bin/python` with a valid `pyvenv.cfg`
- **AND** an inherited runtime root may name a different outer worktree
- **WHEN** the runtime bootstrap dispatches that semantic Python request
- **THEN** it executes the original request directly
- **AND** it does not invoke `uv sync` or a nested `uv run`
- **AND** an unmarked, unavailable, invalid, or non-semantic request retains
  its existing runtime-bootstrap behavior
