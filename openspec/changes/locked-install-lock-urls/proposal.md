# Proposal

## Why

On 2026-11-24 every job of a proposal ref's push run on GitHub failed within 40 seconds, in the
step that prepares the locked tool supply (run 45293766508). Mise had downloaded the
python-build-standalone build `20261123` of CPython 3.14.10, published that day, and compared it
with the checksum of the build `20261110`. The lock records that checksum and the URL of that
build. The lane had not touched the supply, and the same job had passed three hours earlier.

The cause is the mode in which ETHOS runs an install, not the Mise release:

- `tools/ci/toolchain/native.py` installs the declared tools through `run_mise`, and the product
  provisions a tool through `download_tool`. Both run Mise in safe mode over a disposable copy of
  the configuration and its lock, and carry the root's native trust to that copy.
- The designs of 2026-10-25 and 2026-10-26 record that Mise 2026.10.19 read a lock's download
  URLs in safe mode when the copy carried trust or a CI marker was set. Mise 2026.11.9 and
  2026.11.12 do not: in safe mode they load the copy as untrusted whatever trust it carries. For
  an untrusted configuration, Mise's security page says that "the lockfile only pins versions and
  checksums" and that Mise "downloads from where the backend normally would instead of the
  lockfile's URLs".
- For CPython the backend resolves the newest build of the version. Each time the publisher
  rebuilds a locked version, every install without a cached archive fails the locked checksum
  until the lock moves. The same refusal on 2026-11-13 was answered by moving the lock to the
  build `20261110` (Change `supply-move-1114`, decision 3); its mechanism was not found then.

Measured on macOS arm64 on 2026-11-24, each run with an empty data directory and the lock as
committed, each run being `install --locked python`:

- In a trusted project, outside safe mode, with Mise 2026.11.9 and with 2026.11.12: it passes
  and installs the build `20261110`.
- Through `run_mise`, with and without a CI marker, with both releases: it fails on the checksum
  of the build `20261123`.
- In a trusted project with `MISE_SAFE=1`, with 2026.11.12: it fails in the same way.
- With `run_mise`'s environment less safe mode, with 2026.11.9: it passes and installs the build
  `20261110`, whether the copy carries trust, a CI marker is set, or neither.

## What Changes

- An install's safe mode follows the trust that its disposable copy carries. A copy that carries
  the root's native trust is installed outside safe mode, so Mise takes each archive from the URL
  that the lock records and checks it against the recorded checksum. A copy that carries no trust
  stays in safe mode, as now.
- One function states this rule, and both installs use it: `run_mise` for an `install` command,
  and `download_tool`.
- Mise's state stays in the disposable directory in both cases, and resolution stays in safe mode.
- The lock does not move, and neither does the Mise floor.

No requirement changes. "Disposable mise copies carry only native trust" already states that,
for a trusted configuration, "the one native install in the disposable copy reads that copy's
lock". Under Mise 2026.11 that no longer held for the lock's URLs; this Change restores it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The behaviour returns to what the `quality` capability already requires.

## Impact

- Code: `src/ethos/adapters/toolchain/mise.py` and
  `src/ethos/adapters/repo/runtime/materialization/native_supply.py`.
- Behaviour for a trusted root: a provisioning install is native Mise outside safe mode over the
  copy of the configuration and the lock. The copy's `[settings]` apply, and code that the
  configuration runs at install time can run, as when the user runs `mise install` in that root.
  An untrusted root is unchanged.
- Hosted jobs: under a CI marker native Mise reports the root as trusted, so every hosted install
  takes the lock's own archives again.
- Rollback: revert the commit. Hosted installs then fail again whenever the newest build of a
  locked CPython version is not the locked one.
