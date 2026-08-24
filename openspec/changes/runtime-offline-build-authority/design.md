## Context

See `proposal.md`. The installer already has one uv/lock owner, one source wheel
builder, and one immutable runtime publisher. Its source path nevertheless asks
uv to create two fresh offline environments. An empty cache proves that neither
the build backend nor runtime wheels are carried by the lock itself.

## Goals / Non-Goals

**Goals:**

- Make the materialized source environment an explicit, lock-verified bootstrap
  supply.
- Preserve the existing uv resolver, lock, wheel provenance, runtime digest,
  staging, validation, and activation owners.
- Produce a runtime containing only the production closure and exact ETHOS
  wheel, independent of ambient cache state.

**Non-Goals:**

- A repository wheelhouse, second resolver, package vendoring format, or network
  fallback.
- Replacing uv, changing package-only installation, or broad quality-system
  restructuring.

## Decisions

### Validate the active environment before non-isolated build

The source path runs uv's locked, offline, active-environment check before any
wheel output. Only then may `uv build --no-build-isolation` consume the already
materialized build backend.

Alternative rejected: rely on the uv cache to populate an isolated build
environment. Cache is an optimization and may be absent.

### Project the runtime from the verified supply

The installer copies the active environment using the existing relocation-safe
copy boundary, then runs hash-required strict `uv pip sync` against the exported
production closure. It finally installs the exact content-addressed ETHOS wheel
without dependencies.

Alternative rejected: retain the development environment unchanged. That would
make the runtime larger than its production semantics and preserve accidental
tools as runtime capabilities.

Alternative rejected: introduce a checked-in or generated wheelhouse. That adds
a second durable supply owner when the accepted source environment already
contains the required platform-specific bytes.

### Keep package-only installation unchanged

An installed Git-common runtime remains a self-contained package closure and
follows the existing copied-runtime path. Its source wheel is resolved from the
same Git-common content-addressed package store and verified against the
selected runtime manifest before reuse. The copied production closure already
contains every runtime dependency, so package-only successor materialization
does not require uv, a source checkout, a repository lock, or the absolute
`direct_url.json` path recorded during the preceding installation.

Alternative rejected: retain `direct_url.json` as the package-only authority.
Its absolute file URL records an installation event and becomes stale when the
origin repository moves; it is provenance evidence, not a relocatable package
selector.

## Risks / Trade-offs

- [The source environment is stale or incomplete] -> fail before wheel output by
  checking it against the lock.
- [The copied environment contains development tools] -> remove every package
  outside the hash-bound production requirements with exact sync.
- [Interpreter symlinks escape the copied prefix] -> copy dereferenced bytes and
  retain existing relocation and entrypoint validation.
- [A package-only runtime points back to the repository that created it] ->
  resolve the exact wheel through its validated runtime manifest and local
  Git-common package store; reject missing, ambiguous, or digest-mismatched
  package bytes.

## Migration Plan

1. Validate the source environment against `uv.lock` before building.
2. Build the wheel without build isolation from that verified environment.
3. Copy and strictly prune the environment, then install the exact wheel.
4. Publish only after runtime validation; retain existing rollback and cleanup.
