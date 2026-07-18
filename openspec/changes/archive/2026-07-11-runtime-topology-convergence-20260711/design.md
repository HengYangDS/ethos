## Context

ETHOS already has a strong generated-state topology: local coordination belongs
under `.cache/local-state/` or `.ethos/state/`; generated proof and artifacts
belong under semantic `build/` homes; a Work Lane bootstrap exports
`UV_PROJECT_ENVIRONMENT=build/runtime/venv`. The current implementation stops
one layer too early. Most reusable owner scripts invoke bare `uv run`; several
hooks and proof scripts first select `<repo>/.venv/bin/python`. Consequently a
normal command can create or consume an ignored root environment even though the
product contract says new Work Lane environments belong under `build/runtime`.

This is a product-boundary inconsistency, not merely storage waste. A virtual
environment carries source installation and executable resolution; sharing it
across worktrees can execute the wrong checkout. Conversely, uv's downloaded
wheel/build cache is content-addressed and can be shared safely at the host or
CI-cache boundary when its ownership and invalidation are explicit.

The change affects repository-owned execution surfaces only. It does not assign
authority to an actor, expose a global runtime registry, or require adopters to
share a physical cache layout.

## Goals / Non-Goals

**Goals:**

- Make source-bound Python execution use the current checkout's
  `build/runtime/venv` across interactive product commands, owner scripts, and
  local hooks.
- Define one executable bootstrap, with a minimal stable interface, instead of
  copying `UV_PROJECT_ENVIRONMENT` and cache setup into each caller.
- Keep source environments isolated per checkout; classify uv download caching
  as a host/CI cache policy that is explicit but replaceable.
- Upgrade topology audit from path-only observation to executable-entrypoint
  enforcement for root `.venv` fallback and unbound `uv run` use.
- Preserve compatibility through explicit `ETHOS_PYTHON` or `PYTHON` injection;
  root `.venv` remains ignored migration residue only and is never deleted by
  this change.

**Non-Goals:**

- No global shared virtual environment, cross-checkout lock, Principal registry,
  or new authority surface.
- No deletion, mutation, or retirement of existing root `.venv` directories,
  including foreign Work Lanes.
- No change to the authoritative distinction between local fallback evidence and
  hosted CI evidence; no remote GitLab operation.
- No requirement that every adopted repository use uv, Python, or this product
  repository's physical runner scripts.

## Decisions

### 1. One checkout-bound runtime bootstrap

`tools/ci/scripts/with-python-runtime.sh` becomes the sole product-owned shell
adapter for Python/uv execution. It resolves the current Git worktree root,
exports the intended source environment as `${repo_root}/build/runtime/venv`, and
invokes the requested command. It creates only the host/CI cache directory; `uv`
owns lazy environment materialization. When a hook requests the default managed
interpreter and it is absent, the bootstrap invokes `uv run --group dev python`
with the original Python argv; uv then materializes only that checkout's runtime.
Explicit `ETHOS_PYTHON` and `PYTHON` values remain caller-owned overrides. The
existing `run-ethos-lane.sh` becomes a small
semantic command wrapper over this bootstrap; product owner scripts and hooks
source or invoke it rather than replicating path decisions.

`pre-commit` has one additional requirement: Ruff is a development dependency,
not a runtime import. Its format check therefore invokes
`with-python-runtime.sh -- uv run --group dev ruff ...` rather than assuming an
already-created checkout interpreter contains the development group. This keeps
the hook correct both after a first checkout and after a non-dev product command
has materialized only runtime dependencies.

The bootstrap deliberately accepts an explicit executable command after `--`.
It does not invent a command registry or make arbitrary shell text authoritative.
Its concern is only runtime binding and cache policy.

**Rejected:** per-script exports. They repeat an easy-to-drift policy, leave
hooks exceptional, and make topology audit depend on a growing list of snippets.

### 2. Hybrid cache boundary

`UV_PROJECT_ENVIRONMENT` is always checkout-bound. `UV_CACHE_DIR` defaults to a
host-scoped content-addressed location outside the repository checkout, unless
the caller supplies an explicit CI cache location through `UV_CACHE_DIR` or
`ETHOS_UV_CACHE_DIR`. Hosted CI projections set a workspace/runner-cache path;
local commands inherit the safe host cache default. A cache is never a source,
evidence, authority, or lane-lease carrier.

**Rejected:** checkout-local uv cache. It duplicates immutable downloads across
lanes and conflates source isolation with cache isolation. **Rejected:** global
shared `.venv`. It lets a command execute dependencies installed from another
checkout and defeats source-bound runner semantics.

### 3. Explicit interpreter precedence without root fallback

Where a caller needs Python directly, its precedence is
`ETHOS_PYTHON`, then `PYTHON`, then the bootstrap-managed
`build/runtime/venv/bin/python`; no `<repo>/.venv/bin/python` fallback remains.
If the managed interpreter is absent, the bootstrap synchronizes through uv or
fails with a precise bootstrap error. Hook-time paths use the same resolution;
therefore a repository with hooks cannot silently regress to root `.venv`.

**Rejected:** always call bare `python`. It can resolve an unrelated host
interpreter and makes source dependency availability non-deterministic.

### 4. Audit the capability, not accidental residue

The generated-artifact declaration adds root `.venv` as a denied legacy runtime
home for normal execution, while the topology scanner distinguishes existing
ignored migration residue from an active producer. Entrypoint audit fails any
repository-owned executable script, hook, or provider projection that invokes
`uv run` without the bootstrap or contains an active root `.venv/bin/python`
fallback. Tests assert the bootstrap export contract, all owner/hook callers,
and deliberate bad-entrypoint findings.

This gate applies to product-owned executable surfaces. Narrative documents,
archived chronicles, parity snapshots, and adopter-private legacy state are not
rewritten merely because they mention an older command.

The bootstrap requirement begins only after a runtime exists. Two constrained
host-bootstrap adapters remain exempt: `bootstrap-python.sh` installs the
toolchain in an empty hosted image, and `configure-git-checkout.sh` performs
checkout configuration before repository runtime ownership is available. They
MUST NOT run product modules or be used as general execution entrypoints; every
other product Python or uv producer is bootstrap-bound.

## Runtime model

```text
current Git checkout
  -> runtime bootstrap
       -> source environment: <checkout>/build/runtime/venv
       -> dependency cache: explicit CI cache OR host content-addressed cache
       -> uv/Python command
  -> generated evidence/artifacts: existing semantic build homes
```

The environment is a checkout-local substrate. The cache is a replaceable
acceleration substrate. Neither is proof or authority. Work Lane leases remain
under ignored local state and continue to coordinate writes only.

## Risks / Trade-offs

- **[First command synchronization is slower]** → bootstrap creates the
  checkout-local environment lazily; shared downloads avoid repeating network
  fetches.
- **[Hooks run before a checkout runtime exists]** → the bootstrap synchronizes
  only the default checkout interpreter through uv; explicit interpreter
  overrides retain existing caller-owned behavior, and tests cover both paths.
- **[A non-dev command created the checkout runtime first]** → the format hook
  requests its explicit dev group through the same bootstrap, rather than
  mistaking interpreter existence for quality-tool availability.
- **[CI cache location varies by provider]** → provider projections set the
  environment explicitly; the bootstrap has no provider-specific path baked in.
- **[Legacy root environments exist]** → leave them ignored and non-authoritative
  for one migration window; remove only through explicit local operator action
  after verifying no active process uses them.
- **[Cross-lane concurrency]** → per-checkout venvs prevent source mixing;
  content-addressed uv cache is managed by uv and does not carry lane state.
- **[Provider projections overlap another lane]** → under the current
  user-authorized integration decision, this lane updates only the four named
  provider producer surfaces and their template sources, then proves checked
  template/projection parity. The foreign lane is neither mutated in place nor
  retired here; its later handoff or supersession remains an independently
  evidenced lifecycle decision.

## Migration Plan

1. Add bootstrap, contract declaration, audit checks, and tests while root
   `.venv` remains ignored migration residue.
2. Route product owner scripts, hooks, named hosted/local provider projections,
   and local emulator wrappers through the bootstrap; update Work Lane payload
   and docs to describe the hybrid boundary.
3. Run focused synthetic tests proving one checkout's bootstrap cannot choose a
   root `.venv`, then the full proof and local fallback CI on an immutable lane
   HEAD.
4. Land and close out through the normal candidate train. After local acceptance,
   individual developers may delete obsolete root `.venv` directories; no
   automated cleanup or foreign-lane action is permitted.

Rollback is a normal tracked revert of bootstrap routing and policy. It does not
restore or depend on any deleted environment because no environment is removed.

## Open Questions

None. The physical host cache default is intentionally an implementation
adapter, while the immutable contract is its host/CI boundary and explicit
override behavior.
