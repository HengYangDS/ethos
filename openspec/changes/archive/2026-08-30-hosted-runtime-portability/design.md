## Context

Two failures share one portability defect: host-specific execution coordinates
are inferred from Linux-shaped paths. `bootstrap-python.sh` couples the absence of
either Git or `ldconfig` output to Debian `apt-get`, while `DeliveryPipeline`
assumes every `nodejs-wheel-binaries` wheel stores Node under `bin/`. The former
misclassifies Darwin; the latter is false for Windows wheels, where `node.exe`
lives at the package root.

## Goals / Non-Goals

**Goals:**

- Select bootstrap prerequisites by the observed operating system.
- Resolve and validate the package-local Node/npm inputs at one boundary.
- Make all current build and package-only test consumers use the same resolver.
- Preserve offline, lock-bound wheel construction.

**Non-Goals:**

- No package-manager abstraction, compatibility registry, fallback PATH search,
  retry layer, or provider-specific duplicate command body.
- No changes to dependency versions or distribution contents.
- No tempfile, state-schema, adopter-migration, or general CI redesign work.

## Decisions

### Host bootstrap remains a shell-owned projection

The existing bootstrap script will use `uname -s` to choose the only supported
host prerequisite path. Linux may install missing Git or `libatomic` through
`apt-get` when that manager exists. Darwin requires Git and performs no Linux
linker or package-manager probe. Unknown hosts fail with a precise diagnostic.

### One package-local runtime resolver

`tools.ci.toolchain.node` will resolve Node and npm from the installed
`nodejs_wheel` package root. It owns the platform layout distinction, verifies
that Node is a file and executable and that npm's CLI file exists, and returns
the two paths directly. It never consults ambient PATH.

`DeliveryPipeline`, isolated-wheel smoke tests, and release identity builds will
consume this resolver. The Hatch hook remains intentionally ignorant of package
layout and receives only the already validated coordinates through its existing
environment boundary.

## Risks / Trade-offs

- A future upstream wheel layout change will fail at the resolver with exact
  missing paths instead of surfacing as a backend `FileNotFoundError`.
- Shell behavior cannot execute natively on Windows, so the bootstrap regression
  proves Darwin/Linux dispatch with controlled command stubs while hosted Windows
  conformance proves the actual wheel layout.

## Verification

Run strict OpenSpec validation, focused resolver/bootstrap tests, build-hook and
wheel identity tests, shell lint, distribution architecture tests, and then the
single exact-head full proof. After acceptance, publish `dev` before `main` and
require current GitHub and GitLab exact-head CI success.
