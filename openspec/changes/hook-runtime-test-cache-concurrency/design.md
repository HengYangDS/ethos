## Context

See [proposal.md](proposal.md). The expensive immutable hook runtime is needed
by many governed-repository fixtures. Under pytest-xdist, worker-local temporary
roots caused duplicate templates, while a global lock enclosing both template
construction and each roughly 284 MB repository clone serialized consumers.

## Goals / Non-Goals

**Goals:**

- Build and publish at most one valid template for a source/platform identity.
- Let independent repositories clone that immutable template concurrently.
- Preserve one distinct runtime directory per Git common directory.
- Reject incomplete, stale, or source-mismatched templates before reuse.

**Non-Goals:**

- No production cache, runtime-selection, or hook-install behavior changes.
- No persistent test-state authority or replacement for package/runtime
  validation.
- No new dependency; the existing `filelock` test dependency remains the
  cross-process publication primitive.

## Decisions

### One run-level cache root

Normalize each xdist `popen-gw*` base directory to its parent so all workers in
the same pytest run derive the same content-addressed template root. A local,
non-xdist run keeps its own run root. This is narrower than a host-global cache
and cannot survive as hidden authority across unrelated runs.

### Lock only publication

Build and publish the shared template in the pytest controller before xdist
workers start and before per-test timeouts begin. Hold a `FileLock` while
locating or constructing that template, then release it before workers clone
into repository Git common directories. Template publication uses a unique
staging directory, rebinding at its final cache path, and atomic rename, so
readers see either no template or a complete path-valid candidate. Workers may
recover a missing or rejected template under the same lock, but normal xdist
execution does not build one during test setup.

### Validate before reuse, separate mutable leaves

Use the production runtime validator before accepting a cached template. Clone
the immutable package tree with filesystem hard links outside the publication
lock, while giving every repository independent directories and independent
copies of the runtime Python, command entrypoint, and manifest that product
code or adversarial tests may mutate. Test subprocesses disable bytecode writes,
so the remaining linked package files are read-only inputs rather than hidden
cross-worker state.

## Risks / Trade-offs

- **A new runtime-mutating surface is introduced** -> it must be added to the
  explicit mutable-leaf set and the isolation regression before the cache may
  share its bytes.
- **A builder dies before publication** -> the unique staging directory is
  removed best-effort; no incomplete target becomes selectable.
- **A moved template retains its bootstrap shebang** -> publication finalizes
  and validates the runtime at its final cache path before any worker can select
  it.
- **A published template is corrupt** -> validation rejects it and a later
  invocation rebuilds under the publication lock.

## Migration Plan

The change is confined to test support. Rollback removes the cache fixture and
returns to per-test production runtime construction; no repository or runtime
state migration is required.
