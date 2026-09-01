## Context

The repository already owns an exact `package-lock.json` and prepares
`node_modules` through `npm ci --ignore-scripts` before package work. The Hatch
hook ignores that prepared closure: it copies the manifests into a new
`TemporaryDirectory`, invokes npm again with `--offline`, and then packages the
new tree. A different HOME or npm cache therefore changes whether identical
source can build, and each build creates another high-inode dependency tree.
GitLab exact-HEAD jobs `34205` and `34233` reproduced this boundary at accepted
commit `eee7ba5a212730d363e883f4340e39e103feb8d9`; job `34205` failed on the
uncached `zod-4.4.3.tgz`, and its captured log has SHA-256
`5629070f376efdffd8a032a9bf4952908d5fe323d7ad34d89834e24c330a5d78`.

## Goals / Non-Goals

**Goals:**

- one repository-prepared OpenSpec production closure per checkout;
- exact validation against the selected source tree's `package-lock.json`;
- zero npm or network execution inside artifact construction;
- the same closure in wheel and sdist outputs;
- deletion of per-build supply trees and redundant node/npm bindings.

**Non-Goals:**

- a new npm cache, package mirror, vendored tarball registry, or lock format;
- general hosted test PATH repair or identity-drop policy;
- tempfile dead-owner scavenging;
- changes to the OpenSpec version or runtime activation transaction.

## Decisions

### 1. The lock selects; the prepared tree supplies

`package-lock.json` remains the sole Node dependency selection authority. The
build owner binds one prepared `node_modules` root. The hook validates every
non-development, non-link package entry by exact path and package version, then
selects only the outermost production package roots for inclusion. It does not
resolve dependencies or call a package manager.

Alternative rejected: populate or copy an npm cache for each build. A cache is
an implementation aid, not the artifact input, and does not remove the second
resolution/install step.

### 2. Reuse the existing build-input boundary

The two current build variables that expose Node and npm executables are
replaced by one path binding for the already prepared OpenSpec supply. The
delivery pipeline and source-runtime materializer provide that binding. Tests
that build an isolated Git tree reuse the repository supply through the same
binding rather than copying `node_modules` into each fixture.

Alternative rejected: discover a host-global npm cache or walk to another
checkout. Neither is an exact source input.

### 3. Package the same production roots into wheel and sdist

For a wheel, selected roots map under
`ethos/data/openspec-runtime/node_modules`. For an sdist, they map under
`node_modules`, so a wheel built from that sdist consumes the same prepared
closure without npm. Development-only packages and workspace links are never
included.

### 4. Fail before artifact mutation

Missing manifests, absent packages, version drift, symlinks, or undeclared
nested package roots fail during hook initialization with a stable supply gap
and an exact `npm ci --ignore-scripts` provisioning action. No partial artifact
or temporary dependency tree is created.

## Risks / Trade-offs

- The sdist becomes larger because it is self-contained for the OpenSpec
  runtime. This is the same production payload already required by the wheel
  and removes network-dependent reconstruction.
- Installed package contents are validated by exact lock path and version, not
  by re-downloading tarballs. `npm ci` remains the native integrity verifier at
  the single preparation boundary.
- A stale prepared tree now fails immediately instead of being silently
  replaced during a build.

## Migration Plan

1. Add RED tests proving the hook rejects missing/drifted supply and performs no
   npm or temporary-tree work for a valid prepared closure.
2. Replace npm execution with lock compilation and direct force-includes.
3. Route existing build callers through the one prepared-supply binding and
   delete Node/npm build variables and tests.
4. Prove wheel, sdist, isolated source identity, package-only install, CI
   projection, and repository-wide retired-reference closure.
