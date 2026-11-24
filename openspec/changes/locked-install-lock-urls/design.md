# Design

## Context

Two places install tools with native Mise over a disposable copy of a repository's configuration
and lock:

- `run_mise` in `src/ethos/adapters/toolchain/mise.py`. Every call from the product is offline
  resolution. `tools/ci/toolchain/native.py` also calls it online, to install the declared Node.js,
  Python, uv, CUE, actionlint and Go for ETHOS's own hosted jobs and supply image.
- `download_tool` in `native_supply.py`, through which `materialize_tool` provisions Node.js and
  the locked native tools.

Both set `MISE_SAFE=1` and add what `carried_trust` returns: the path of the copy's configuration,
when native Mise reports the root as trusted. The design of 2026-10-25 chose this pair. It records
that Mise 2026.10.19 read the lock entries and download URLs of such a copy, wrote no trust record
and ran no repository code.

Mise 2026.11.9 and 2026.11.12 treat a copy in safe mode as untrusted whatever path it carries. An
untrusted lock pins versions and checksums; the download comes from where the backend resolves.
Outside safe mode the same releases take the lock's URL for a trusted copy. They also take it for
a copy that nobody trusted: `mise install` trusts its active configuration by itself and writes a
trust record into its state directory.

Under a CI marker native Mise reports a root as trusted: `mise trust --show` prints `trusted`
with `CI=true` or `GITHUB_ACTIONS=true` and `untrusted` without, with both releases. So
`carried_trust` already carries trust on every hosted job and in the supply image's CI-mode
stages.

## Goals / Non-Goals

**Goals:**

- A trusted install takes the archive at the URL that its lock records.
- An untrusted configuration gains no trust and its install is unchanged.
- The rule is stated once.

**Non-Goals:**

- Changing resolution, which stays in safe mode.
- Moving the lock, the Mise floor or the supply image.
- Changing Mise, or what counts as trusted.

## Decisions

1. **Trust selects the mode.** `install_mode` returns the carried trust for a trusted copy and
   `MISE_SAFE=1` for any other. `run_mise` applies it when its command is `install`, in place of
   the safe mode that resolution sets, and `download_tool` applies it in place of its fixed safe
   mode. The command decides, so no caller passes a second statement of what it runs.
2. **An untrusted copy stays in safe mode.** Outside safe mode its install would trust it, and
   "Disposable mise copies carry only native trust" forbids trusting a configuration that native
   Mise does not report as trusted. Its result is what it is today: versions and checksums are
   pinned, and a rebuilt archive is refused by its checksum.
3. **State stays disposable.** Both installs keep `MISE_STATE_DIR` inside the copy. Outside safe
   mode, Mise 2026.11.9 writes a trust record there for a copy that carries a trusted path, and
   none under a CI marker. The record is removed with the copy, so no trust outlasts the invocation
   and the host's state is unchanged. This Change reads the requirement's "SHALL write no trust
   record" as a record that outlasts the invocation.
4. **The caller's own safe mode does not reach an install, as before.** Resolution replaced it,
   and `download_tool` never passed it. Passing it on would make it a runtime input that
   `system/surfaces.toml` has to declare, for a choice that no caller of the two installs makes:
   both serve `tools/ci/toolchain/native.py`, and no CI carrier of ETHOS selects safe mode.
5. **Both installs, one rule.** No failure of `download_tool` is known. Its tools are Node.js and
   release archives that are named by version, where the backend and the lock name the same file
   unless a publisher replaces it. It rests on the same assumption and the same requirement, so it
   is repaired with the hosted install.

## Rejected alternatives

- **Move the lock to the build of 2026-11-23.** This is the answer of 2026-11-14. It fails again
  at the next rebuild, and that build is younger than the release age of 24 hours until
  2026-11-25 01:34 +08:00.
- **Raise the Mise floor.** 2026.11.12 behaves as 2026.11.9 does.
- **Leave safe mode for every install.** An install would then trust a configuration that nobody
  trusted.
- **Install outside the disposable copy.** The copy holds the exact declared bytes and keeps
  Mise's state off the host; both requirements stand.

## Risks / Trade-offs

- [Code that a trusted configuration runs at install time now runs during provisioning, also for
  a caller whose own environment selects safe mode] → The user or the CI has trusted that root,
  and native `mise install` there runs the same code. The copy holds only the configuration and
  the lock, and its state is discarded. ETHOS's own configuration declares no hook, no `[env]`
  and no install-time option.
- [Mise changes safe mode or trust again] → The rule is one function. A wrong archive is still
  refused by the locked checksum, so the failure is a refused install and not an unverified one.
- [No test downloads through real Mise] → The unit tests bind the environment of both installs in
  both trust states. The proposal ref's push run is the test of the download: it fails in every
  job before this Change and installs the locked build after it.
