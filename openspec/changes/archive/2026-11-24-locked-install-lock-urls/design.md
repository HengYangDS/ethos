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
2. **The install is a module of its own, and `run_mise` has no mode.** `run_mise` runs every
   command in safe mode, as it does on `dev`; it takes no argument that could change that. The new
   module `adapters/toolchain/mise_install.py` holds `install_mode` and
   `install_locked(root, tools)`. The entry reads the configuration and the lock from the root
   with `repository_mise_files`, never from a caller, and runs `install --locked -- <tools>` in
   the copy that `disposable_copy` yields, with that copy's environment passed through
   `install_mode`. `disposable_copy` is the part that `run_mise` and the entry share. Every copy
   is made there, so the checks that `run_mise` made of its declarations moved there with it: a
   missing configuration or lock, a path that leaves the copy, and a version carrier that changed
   under the root are refused for the install as for any run. The tool names follow `--`, so
   none of them is read as an option. Measured with Mise 2026.11.9:
   `install --locked --cd <directory>` installs from that directory's configuration, and after
   `--` the same words are refused as unknown tools.
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
8. **Sizes.** `run_mise` keeps one decision, so its entry of 17 leaves the baseline of pinned
   decision counts; the checks it held are `_exact_declarations`, which measures 14 against the
   threshold of 15. `mise.py` holds 496 effective lines against the ceiling of 500 for one file,
   and the new module 34.
9. **The integrity gate binds the new module.** The list of product sources that take part in a
   CUE projection names `adapters/toolchain/mise.py` and `native_supply.py`. The rule that
   decides the provisioner's mode now lives in `mise_install.py`, so the list names it too, and
   an edit of the rule changes the gate's bound material as before.

## Rejected alternatives

- **Move the lock to the build of 2026-11-23.** This is the answer of 2026-11-14. It fails again
  at the next rebuild, and that build is younger than the release age of 24 hours until
  2026-11-25 01:34 +08:00.
- **Raise the Mise floor.** 2026.11.12 behaves as 2026.11.9 does.
- **Leave safe mode for every install.** An install would then trust a configuration that nobody
  trusted.
- **Select the mode inside `run_mise`.** Three forms were written and reviewed: the command's
  first argument, a function passed as an argument, and a private object passed as an argument.
  Each left a way to reach an install's mode through `run_mise`, and the last two were held by a
  test that read the source. Five reviews in a row found a way in, three of them around such a
  test. With the install in a module of its own there is nothing in `run_mise` to reach.
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
- [Any product code can call `install_mode` and start Mise itself] → That code would be a second
  install, written on purpose. This Change guards against reaching an install's mode by
  oversight through the shared runner, not against a second implementation; no test reads the
  source for one.
- [No test downloads through real Mise] → The unit tests bind the environment of both installs in
  both trust states. The proposal ref's push run is the test of the download: it fails in every
  job before this Change and installs the locked build after it.
