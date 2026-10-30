# Proposal

## Why

`0.2.0-alpha.20` publishes no `windows-arm64` archive, so Mise finds no ETHOS asset on a Windows
ARM64 host. DDWG's GitLab Windows verification runs on such a host and fails before any check.

A native runtime for that platform is blocked upstream. `cel-expr-python` 0.1.3, the CEL engine of
ETHOS's policy kernel and its latest release, publishes neither a `win_arm64` wheel nor a source
distribution. Windows on Arm runs x64 programs through its built-in emulation, so an x64 runtime
can serve the platform. Two defects stand in the way:

- **ETHOS names an architecture after the host CPU.** From Python 3.12, `platform.machine()` on
  Windows asks WMI for the native processor, so an emulated x64 interpreter reports `ARM64`.
  - Runtime selection compares the manifest's `x86_64` with that `ARM64` and refuses the runtime.
  - The build selects arm64 Node and Vale for an x64 interpreter, and tags a wheel that interpreter
    cannot install.
- **Publication keys each archive by its runtime.** A Windows ARM64 host that qualifies an x64
  runtime has no platform of its own in the release.

## What Changes

- **The interpreter's machine.** ETHOS reads one fact, the machine its interpreter executes.
  - On POSIX this is `uname`, as today.
  - On Windows it is the interpreter's build platform from `sysconfig`.
  - Runtime manifests and selection, native-tool and Node supply, the Python image observation and
    the CI Mise staging all read it. Every native host observes the same values as before.
- **Declared hosts.** Each release leg declares the one host platform it qualifies and uploads its
  qualification under that name. The host is declared rather than observed, because Windows
  reports its CPU to an emulated interpreter.
- **Host-keyed publication.**
  - Each archive and Mise platform is named for its leg's host.
  - A wheel is published only for a host that executes it natively. An emulating host publishes
    its archive alone.
  - `linux-arm64`, `linux-x64` and `macos-arm64` stay required and natively qualified.
- **A Windows ARM64 leg.** Host conformance and the hosted release add a `windows-11-arm` leg that
  builds and qualifies with the x64 CPython. Windows release legs stay optional.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `distribution`: platform support may come from a runtime that the host's operating system
  emulates, once that host qualifies those exact bytes.

## Impact

- **Product code.** `src/ethos/adapters/repo/runtime/manifest.py` gains the interpreter machine
  beside `canonical_architecture`. Runtime selection, native supply, Node supply and the Python
  observation read it.
- **Delivery code.** `tools/ci/toolchain/native.py` and `tools/ci/delivery/release_assets.py`.
- **CI.** `.config/ci/pipeline.cue` and the generated `.github/workflows/ci.yml` add the
  `windows-11-arm` legs and declare each release leg's host. GitLab is unchanged.
- **Unchanged.** Dependencies, lock files, the supply image and every native host's runtime
  identity.
- **Adopters.** A Windows ARM64 host installs the `windows-arm64` archive through Mise once a
  release carries it. DDWG rebinds to that release.
