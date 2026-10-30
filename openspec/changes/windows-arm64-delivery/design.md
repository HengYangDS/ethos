# Design

## Context

`0.2.0-alpha.20` qualifies and publishes four platforms: `linux-arm64`, `linux-x64` and
`macos-arm64` are required, and `windows-x64` is optional. DDWG verifies on GitLab's
`ci-windows-arm64-shell` runner, a Windows 11 ARM64 host, where Mise finds no ETHOS asset.

- **Native is blocked upstream.** `cel-expr-python` 0.1.3, the latest release, publishes no
  `win_arm64` wheel and no source distribution. The latest releases of six more dependencies
  publish no `win_arm64` wheel either and would need source builds: `cryptography`, `lychee-bin`,
  `pyyaml-ft`, `setproctitle`, `shellcheck-py` and `shfmt-py` (PyPI, 2026-10-30). Every tool in
  `.config/mise/mise.lock` already has a `windows-arm64` entry.
- **The machine ETHOS reads.** Seven call sites read `platform.machine()`:
  - the runtime environment default in `manifest.py`, and runtime selection in `selection.py`;
  - native-tool supply in `native_supply.py`, and Node supply with the wheel tag in
    `node/supply.py`;
  - the Python image observation in `python_environment.py`;
  - the CI Mise target and cache path in `tools/ci/toolchain/native.py`.
- **CPython's report.** Since 3.12, CPython on Windows answers `platform.machine()` from WMI's
  `Win32_Processor.Architecture`, the native CPU. An x64 interpreter that Windows on Arm emulates
  therefore reports `ARM64` ([cpython#98962](https://github.com/python/cpython/issues/98962)). That
  issue is still open: requests to report the emulated architecture continue. From 3.13, one
  failed WMI query makes the process fall back to environment variables, which name `AMD64`.
  `sysconfig.get_platform()` names the interpreter's own build, `win-amd64` or `win-arm64`, and
  uv takes wheel tags from it.
- **Hosted runners.** GitHub offers `windows-11-arm` to public repositories at no cost. In
  alpha.20's release run the `windows-latest` leg took 43 minutes.

## Goals / Non-Goals

**Goals:**

- A Windows ARM64 adopter installs a qualified ETHOS archive through Mise.
- One rule names the machine ETHOS executes, and every native host observes the same values as
  before.
- A host platform is declared only after its own release smoke qualified the archive it receives.

**Non-Goals:**

- A native ARM64 runtime for Windows. It waits for `win_arm64` wheels of `cel-expr-python` and the
  six packages above.
- macOS Rosetta and Linux user-mode emulation.
- GitLab release legs, and DDWG's runner bootstrap, which the shared-ownership design covers.

## Decisions

1. **The interpreter's machine, not the CPU.**
   - `process_machine()` in `manifest.py`, beside `canonical_architecture`, returns
     `platform.machine()` on POSIX, where `uname` already reports the process's view.
   - On Windows it maps `sysconfig.get_platform()`: `win-amd64` to `AMD64` and `win-arm64` to
     `ARM64`. This is the spelling `platform.machine()` returns on a native host, so cache paths,
     digests and manifests do not change there.
   - The seven call sites read it. The Python image observation reports the same mapping from the
     interpreter it observes.
   - **Alternative rejected:** keep the CPU and teach selection an emulation table. The build would
     still select arm64 Node and Vale for an x64 interpreter, and every site would need the table.
2. **Declared hosts, host-keyed publication.**
   - The release matrix has one axis, `host`. Each leg's runner and interpreter serve that host,
     and the leg uploads its qualification as `release-runtime-<host>`.
   - The assembler names each archive and Mise platform for that host. A leg whose runtime runs
     another operating system is refused. The assembler publishes a wheel only where host and
     runtime agree, and requires the three required platforms natively.
   - **Alternative rejected:** record the host from `platform.machine()`. Its Windows answer
     depends on WMI and on an open CPython question. A fallback would name the arm leg
     `windows-x64`: it would either fail the whole release as a duplicate, or publish emulated
     bytes as native ones.
   - **Alternative rejected:** declare `windows-arm64` with the `windows-x64` archive's bytes after
     a dependent job qualifies them. It would couple the platforms, wait behind the 43-minute leg,
     and qualify through the shared-supply proof rather than the release smoke every platform runs.
3. **One emulated leg per workflow.**
   - `windows-11-arm` with `cpython-3.14-windows-x86_64-none` joins host conformance for Python
     3.14 only, and the release matrix as the `windows-arm64` host.
   - Windows release legs stay optional. The host-conformance leg is required: it is the
     continuous qualification of the emulated path.

## Risks / Trade-offs

- **Emulation is slow.** The leg may become the longest in a run, and it gates every push. →
  Python 3.14 only. Task 3.2 measures it on the proposal run before landing.
- **A leg could declare the wrong host.** → A test pins every release leg's host to its runner and
  interpreter, and the assembler refuses a runtime of another operating system.
- **Hosted acceptance stops before the consumer.** The leg installs from one archive URL through
  an emulated x64 Mise. An adopter's native Mise resolves the `windows-arm64` key instead. → The
  release's acceptance includes DDWG's GitLab Windows job installing the release on
  `ci-windows-arm64-shell`.
- **Emulating hosts move their tool caches** from `Windows_ARM64` to `Windows_AMD64` once. → Hosted
  runners keep no cache; a local host downloads again.

## Migration Plan

- Land, then publish `dev` and `main` to both peers. `0.2.0-alpha.21` carries the `windows-arm64`
  archive.
- DDWG rebinds to that release, and its Mise declaration gains the platform from the release's
  `mise.toml`. Its GitLab Windows job passing on `ci-windows-arm64-shell` accepts the platform.
- **Rollback.** Revert this Change. A release without the leg omits `windows-arm64`, as alpha.20
  does.

## Open Questions

- None blocking. The release owner requests `win_arm64` wheels from the `cel-expr-python`
  maintainers and reviews the seven packages again on 2026-11-30. A native runtime would then
  replace the emulated archive.
