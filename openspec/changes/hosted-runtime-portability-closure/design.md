## Context

See proposal.md. The same candidate passed source construction and POSIX package
conformance, then failed at two host boundaries: Windows runtime materialization
could not rediscover the installed `ethos` entrypoint, while Linux identity-drop
tests could not read the root-owned checkout even though the runner had declared
an exact `safe.directory` overlay.

## Goals / Non-Goals

**Goals:**

- Preserve installed distribution metadata and entrypoint identity through one
  immutable runtime-image path on every supported host.
- Preserve an explicitly declared Git configuration overlay through the one
  shared Git subprocess owner.
- Keep both fixes deterministic, fail-closed, and covered by hosted-equivalent
  regressions.

**Non-Goals:**

- Adding Windows launcher fallbacks or hard-coded script names.
- Inheriting ambient Git configuration or trusting arbitrary directories.
- Adding per-test workarounds, provider branches, or another environment model.
- Solving unrelated lane-start, tempfile, documentation, or lifecycle gaps.

## Decisions

### Preserve package metadata before interpreting entrypoints

The runtime image already installs the exact wheel before entrypoint discovery.
Discovery will operate on that image's actual platform site-packages layout and
distribution metadata. The materializer will not infer `ethos.cli:main` from
source or treat a pre-existing launcher file as authority.

Alternative rejected: special-case Windows by accepting `Scripts/ethos.exe`.
That file is a generated projection and does not prove which installed
distribution owns the entrypoint.

### Pass explicit Git configuration through the Git owner

The proof runner already constructs a bounded indexed overlay containing exact
repository trust and deterministic fixture settings, while the test process
declares author/committer identity through Git's native environment. `run_git`
will preserve those exact inputs, but will not project `user.name` or
`user.email` over repository-local identity policy. It still removes ambient
repository/ref/index overrides and forces empty global and system
configuration.

Alternative rejected: configure every failing test or change checkout
ownership. Both bypass the shared execution boundary and make hosted behavior
depend on fixture placement.

## Risks / Trade-offs

- **Malformed inherited indexed configuration could become observable** → accept
  only complete numbered key/value pairs and fail closed on malformed input.
- **A broad `safe.directory` could weaken trust** → the runner supplies exact
  checkout coordinates; focused tests reject wildcard or unrelated entries.
- **Platform path simulation may miss native packaging behavior** → keep the
  focused unit RED and require the existing Hosted Windows package smoke before
  accepted closeout.

## Migration Plan

1. Add focused failing regressions for Windows metadata discovery and
   identity-dropped Git execution.
2. Repair the two existing owners and remove any now-redundant local handling.
3. Run focused and affected gates, exact-HEAD proof, archive/reproof, and
   candidate projection.
4. Advance the existing proposal ref to the new exact object and require both
   Hosted providers to pass before accepted closeout and runtime activation.
