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

Hold a `FileLock` while locating or constructing the shared template. Release
it before cloning into a repository's Git common directory. Template
publication uses a unique staging directory and atomic rename, so readers see
either no template or a complete candidate.

### Validate before reuse, detach mutable leaves

Use the production runtime validator before accepting a cached template. Clone
the immutable tree with hard links where supported, then detach the manifest
and launcher files that repository finalization rewrites. This preserves byte
reuse without allowing one fixture to mutate another fixture's runtime.

## Risks / Trade-offs

- **Hard links are unavailable or cross-device** -> the existing copy operation
  fails visibly rather than silently falling back to a divergent cache model.
- **A builder dies before publication** -> the unique staging directory is
  removed best-effort; no incomplete target becomes selectable.
- **A published template is corrupt** -> validation rejects it and a later
  invocation rebuilds under the publication lock.

## Migration Plan

The change is confined to test support. Rollback removes the cache fixture and
returns to per-test production runtime construction; no repository or runtime
state migration is required.
