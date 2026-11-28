# Proposal

## Why

The owner decided on 2026-11-25 that ETHOS ends its Windows support entirely, in CI and everywhere
else, and that the same holds for every governed repository. ETHOS then runs on GitHub on arm macOS,
arm Linux and x86 Linux, and on GitLab on arm macOS and arm Linux; the arm macOS job on GitLab
arrives with a later Change (Out Of Scope).

Windows was never a platform that a release had to publish: its two release legs were optional, its
suite leg was allowed to fail, and no adopter journey ran there. It still cost a second code path in
the product (access-control lists, a process listing through the management interface, a second
launcher, a second archive form, a read path without descriptor chains), four hosted legs, supply
digests for two platforms, and tests that simulated a host which no gate required.

## What Changes

- The product keeps one path, the POSIX one. Every branch on the Windows platform leaves, with the
  code only it reached: the access-control reading of a trust anchor, the management-interface
  process listing and its `strict` mode, the `cmd` console launcher, zip archives of Node and of
  native tools, the read path for hosts without descriptor chains, junction checks, the backslash
  and drive-letter checks in resource and Git attribute names, and the platform's kept environment
  names.
- A failed protection of a trust anchor now carries the gap
  `git_object_trust_anchor_protection_failed` with the host's reason on every host, where only the
  Windows path carried it before. The gap `git_object_trust_anchor_observation_unavailable` leaves
  with its only producer, as do `hook_launcher_platform_invalid` and
  `native_node_archive_members_invalid`.
- The hook declaration is read by its `posix` entry. The shipped declaration keeps the entry `nt`,
  because the reader of the releases before this one refuses a declaration without it, and the
  launcher keeps its bytes, the drive-letter alternative of its path pattern included: a changed
  launcher makes the product refuse its own rollback across the change (run on 2026-11-25), so the
  hook generation does not change. Four pieces that exist only for Windows stay, each with the
  condition that ends it (design, "What stays, and until when").
- Releases publish three platforms, each required: `linux-x64`, `linux-arm64`, `macos-arm64`. The
  optional and the emulated release leg leave; release assembly takes one list of hosts and refuses
  a leg whose runtime is not its declared host's.
- Hosted conformance, the suite legs and the common verification model name no Windows runner. The
  dispatch input that added the Windows legs leaves.
- The paradigm's platform vocabulary for retained CI steps is `darwin` and `linux`. A record that
  names `windows` is read for one more release and reported as
  `repository_paradigm_retained_step_platform`, a gap that does not block. It becomes incomplete no
  earlier than the next release, by the owner's decision recorded in the Change that arms it. Shell,
  PowerShell and `cmd` are still detected as script kinds: that is a rule about files, not support
  for a platform.
- The accepted specifications lose 32 scenarios that describe Windows behaviour, by one direct edit
  that the design lists scenario by scenario; ten of them return reworded, for a promise that holds
  on every host. Three further requirements, with six scenarios, leave by `REMOVED`: two return
  under new titles without a platform, and one has no successor. Two requirements are renamed, and
  one loses a step.
- The locks resolve for macOS and Linux only: the Mise lock loses its Windows platform records and
  the Python lock declares its two environments.
- **BREAKING**: a release from this Change on publishes no Windows archive and no Windows wheel. A
  governed repository whose Mise pin lists `windows-x64` or `windows-arm64` for ETHOS takes the step
  that the lane measures on two copies (task 5.4): an upgrade by `ethos lane repair-paradigm --pin`
  drops the rows; what a bind does with rows kept by hand is measured there. A pipeline declaration
  that names the runner system `windows` no longer compiles against the common CI model.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: trust anchors are protected by permission bits alone.
- `distribution`: three required platforms; no emulated or optional leg; one archive form.
- `proof-hosts`: host conformance names macOS and Linux.
- `quality`: conformance tiers, suite legs, the aggregate check and command interruption without the
  Windows cases; the common model generates no Windows job.
- `runtime-activation`: one runtime image layout and one process listing.
- `repository-governance`: the scenario of a retained step names no shell.
- `repository-paradigm`: a retention record that names a leaving platform is reported.

## Impact

- Code: `src/ethos/adapters` (process, toolchain, gates, store, repository runtime, hook, trust
  anchor, content), `src/ethos/application`, `src/ethos/repository`, the paradigm declaration and
  the gap registry; `tools/ci` (toolchain, release supply chain, release assets, acceptance).
- Configuration: `.config/ci/pipeline.cue` and `verification.cue`, the generated GitHub workflow,
  the Mise declaration and lock, `pyproject.toml` and `uv.lock`, the CI projection policy.
- Tests: the Windows-only cases and the host simulation module leave; the density baseline shrinks.
- Adopters: the breaking item above. Read over the fifteen governed checkouts of the owner's host
  (2026-11-25, the pins again on 2026-11-26): four pin ETHOS's Windows archives, one holds a
  retention record with two entries that name `windows`, and none of the seven that compile against
  the common CI model names a Windows runner.

## Out Of Scope

- The detection of PowerShell and `cmd` scripts in a governed tree: it classifies files.
- An arm macOS job in ETHOS's GitLab pipeline, and the rule for what each Forge runs. ETHOS's GitLab
  pipeline runs in the Linux guest alone today; both belong to a later Change, which is not open
  yet.
- The governed repositories' own pipelines and pins.
