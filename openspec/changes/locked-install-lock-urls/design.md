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

1. **Trust selects the mode, and one function owns the rule.** `install_mode` returns an
   install's environment. Without carried trust it sets `MISE_SAFE=1` itself, whatever the
   environment said, so the guarantee does not rest on a caller. Trust is the carried
   configuration path alone. A caller that holds its trust mapping apart, as `download_tool` does,
   passes it as a second argument, and no other entry of that mapping reaches the child: a mapping
   cannot lift safe mode, the search ceiling or the lock.
2. **An install has its own entry, and a token of the module selects its mode.**
   `install_locked(root, tools)` builds `install --locked` itself and runs it through `run_mise`
   without a `files` argument, so the configuration and the lock are the root's own. `run_mise`
   applies `install_mode` only when its `install` argument is `_LOCKED_INSTALL`, an object that the
   module keeps private and that `install_locked` alone passes. A caller therefore cannot choose
   the mode, pass a rule of its own, or give an install a lock that is not the root's; any other
   value leaves the run in safe mode. No command's first argument selects the mode, so a global
   option before `install` cannot keep safe mode without a sign. A test reads the source of the
   product and its tools: the token is named in its module alone, where it is defined once,
   compared once in `run_mise` and passed once by `install_locked`, whose parameters are `root`,
   `tools`, `executable` and `timeout`.
3. **Nothing above a copy is read.** `run_mise`'s environment already ends Mise's search at the
   copy's parent, and `download_tool` now does the same. Measured with Mise 2026.11.9: a
   `mise.toml` in the directory above a copy ran its `[env]` template and its `preinstall` hook
   during an install outside safe mode, although only the copy carried trust, with and without a
   CI marker. With the search ended at the copy's parent, neither ran and the install took the
   locked archive. The provisioner's copy lies in the tool cache, below the repository or its Git
   directory.
4. **An untrusted copy stays in safe mode.** Outside safe mode its install would trust it, and
   "Disposable mise copies carry only native trust" forbids trusting a configuration that native
   Mise does not report as trusted. Its result is what it is today: versions and checksums are
   pinned, and a rebuilt archive is refused by its checksum.
5. **State stays disposable.** Both installs keep `MISE_STATE_DIR` inside the copy. Outside safe
   mode, Mise 2026.11.9 writes a trust record there for a copy that carries a trusted path, and
   none under a CI marker. The record is removed with the copy, so no trust outlasts the invocation
   and the host's state is unchanged. This Change reads the requirement's "SHALL write no trust
   record" as a record that outlasts the invocation.
6. **The caller's own safe mode does not reach an install, as before.** Resolution replaced it,
   and `download_tool` never passed it. Passing it on would make it a runtime input that
   `system/surfaces.toml` has to declare, for a choice that no caller of the two installs makes:
   both serve `tools/ci/toolchain/native.py`, and no CI carrier of ETHOS selects safe mode.
7. **Both installs, one rule.** No failure of `download_tool` is known. Its tools are Node.js and
   release archives that are named by version, where the backend and the lock name the same file
   unless a publisher replaces it. It rests on the same assumption and the same requirement, so it
   is repaired with the hosted install.
8. **`run_mise` keeps its shape.** A private runner under a resolution-only `run_mise` was
   written and withdrawn: the module would have held 517 effective lines against the ceiling of
   500 for one file. The token of decision 2 gives the same reach, a private name of the module,
   in one argument: the function's pinned decision count stays 17 and the module holds 496
   effective lines.

## Rejected alternatives

- **Move the lock to the build of 2026-11-23.** This is the answer of 2026-11-14. It fails again
  at the next rebuild, and that build is younger than the release age of 24 hours until
  2026-11-25 01:34 +08:00.
- **Raise the Mise floor.** 2026.11.12 behaves as 2026.11.9 does.
- **Leave safe mode for every install.** An install would then trust a configuration that nobody
  trusted.
- **Read the mode from the command's first argument.** The first commit of this Change did. A
  global option before `install` would then keep safe mode without a sign; the review of that
  commit named it.
- **Pass the mode to `run_mise` as a function.** The second and third commits did. Any caller
  could then pass a mode, and any function as one; a test of the source that looked for such
  calls had to name every way of reaching a function, and three reviews each found another.
- **Install outside the disposable copy.** The copy holds the exact declared bytes and keeps
  Mise's state off the host; both requirements stand.

## Risks / Trade-offs

- [Code that a trusted configuration runs at install time now runs during provisioning, also for
  a caller whose own environment selects safe mode] → The user or the CI has trusted that root,
  and native `mise install` there runs the same code. The copy holds only the configuration and
  the lock, and its state is discarded. ETHOS's own configuration declares no hook, no `[env]`
  and no install-time option.
- [A configuration above a copy runs its code in an install outside safe mode] → Decision 3: the
  search ends at the copy's parent in both installs. The unit tests bind that entry, and a run
  with native Mise showed the code of the directory above not running.
- [Mise changes safe mode or trust again] → The rule is one function. A wrong archive is still
  refused by the locked checksum, so the failure is a refused install and not an unverified one.
- [Python has no private names, so a module can still import the token] → The test of decision 2
  fails on every reference to the token outside its module, by name or as a string. A name
  computed at run time is not seen; that is the limit of a test of the source.
- [No test downloads through real Mise] → The unit tests bind the environment of both installs in
  both trust states. The proposal ref's push run is the test of the download: it fails in every
  job before this Change and installs the locked build after it.
