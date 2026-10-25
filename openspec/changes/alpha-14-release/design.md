# Design

## Context

See [proposal.md](proposal.md).

- **Resolution and trust.** `run_mise` copies a repository's mise declarations into a disposable directory and runs mise there in safe mode with disposable state. A configuration with any `[settings]` table needs trust. mise trusts by path, so the copy is always untrusted, even when the user has trusted the repository. mise 2026.10.19 keys an aube-locked install (`<version>~aube~<hash>`) by its lock entry only for a trusted configuration; for an untrusted one it looks for the plain `<version>` and reports the tool missing.
- **Per-invocation trust in probes.** `MISE_TRUSTED_CONFIG_PATHS` naming the copy's configuration file, set together with `MISE_SAFE=1` for one invocation, selects the aube install. It writes no trust record, and no template, sourced file, hook or task runs. mise reports trust per configuration root, so `trust --show` still shows such a copy as untrusted; the aube selection checks the file itself.
- **Asking whether the root is trusted.** `mise --cd <root> trust --show`, run under the caller's environment, prints one `<root>: trusted` line per configuration root. The root is printed with the home directory shortened to `~`. The query runs no template, sourced file or hook, even for a trusted configuration, and its answer is the same in safe mode. On a host with no mise state yet, it lets mise create its empty state layout.
- **Provisioning.** `materialize_tool` also runs `mise install --locked` in safe mode over a disposable copy. Outside CI mode, mise 2026.10.19 reads neither aube entries nor download URLs from an untrusted copy's lock, so it cannot provision a tool whose archive is not cached. Cached archives hid this until the supply moved.
- **The JavaScript reporter.** The behavior gate and the gate runner each build the same `NODE_OPTIONS` string, with the reporter given as an absolute path.
- **The supply.** The release owner's inventory of 2026-10-25 lists the latest stable releases that ETHOS's constraints allow, including a Python 3.14 patch release, because `requires-python` excludes 3.15. The CI bootstrap binds one mise release, equal to the floor, with the official executable digests of every platform.

## Goals / Non-Goals

**Goals:**

- Resolution selects what the repository's own trusted configuration selects, and never more.
- Windows runs of the JavaScript behavior gate load the reporter and write the journal.
- ETHOS's own supply at the latest stable releases its constraints allow.
- One accepted head that names and describes 0.2.0-alpha.14.

**Non-Goals:**

- Changing mise, its trust model or adopters' repositories.
- Trusting an untrusted configuration, or refusing untrusted task-only configurations.
- Fixing publish readiness against required checks, or refresh provenance. Later Changes own both.

## Decisions

- **Native mise decides trust, under the caller's inputs.** Before each resolution, ETHOS runs `mise trust --show` in the repository's canonical root with the caller's environment. That environment carries the state directory, global `trusted_config_paths`, `MISE_TRUSTED_CONFIG_PATHS` and the paranoid setting, so mise's own answer covers content-tied trust and worktree inheritance. The query adds only safe mode, which changes no answer and keeps repository code from running. It never runs inside the isolated resolution environment, which hides those inputs.
- **Only an exact line counts.** A line whose path expands (`~` to home) and resolves to the canonical root, followed by `: trusted`, means trusted. Any other output, a failed exit or a query that cannot start means untrusted. A timeout propagates, as for every other native call.
- **Trust carries to exactly one file.** When the root is trusted and the copy's configuration bytes equal the root's own configuration, resolution sets `MISE_TRUSTED_CONFIG_PATHS` to the copy's configuration file, and keeps `MISE_SAFE=1` and disposable state. The byte check matters for content-tied trust, which judges exactly those bytes, and for callers that pass declarations read elsewhere. Provisioning's copy carries the same trust through the same owner, `carried_trust`. Discovery, which runs at the real root, and every execution environment never carry trust.
- **Untrusted means unchanged.** An untrusted root gets today's resolution. A refusal from it appends `next: mise --cd <root> trust`, because the user's own mise refuses that configuration too.
- **One owner for Node's test options.** `execution.node_test_environment(output)` builds `NODE_V8_COVERAGE` and `NODE_OPTIONS` for an attempt's output directory. It passes the reporter as `Path.as_uri()`, which is valid on every platform, and the destination as a file path. `NodeAttempt.environment()` and the behavior gate both use it.
- **`--` ends tool options.** codespell and Vale get `--` before their file lists, as the Lychee calls already do.
- **Supply at the latest stable releases.** The versions come from the inventory.
  - Native lock commands write the locks: `mise lock`, npm, and `uv lock --upgrade`.
  - Moved Python floors follow the lock.
  - `ethos lane project` regenerates the provider projections.
  - The mise floor and the CI bootstrap move together to 2026.10.19, the release the trust behaviour was verified on. Their digests come from that release's official `SHASUMS256.txt`.
  - jdx/mise-action v5 delays only an unpinned mise, and the model always passes `version`.
- **Release entry, as in earlier entries.** Bump the version owner and its projections as exact replacements, and date the entry with the local calendar day on which the tag is created.

## Risks / Trade-offs

- [Each resolution adds one `mise trust --show` process] → It is a read-only query bounded by the existing timeout, and it is far cheaper than the resolution it qualifies.
- [mise changes the `trust --show` format] → Nothing matches, so the root counts as untrusted, and the refusal names `mise trust`. That fails closed.
- [A trusted repository's settings now apply during resolution] → These are the settings the user's own mise already applies to that repository, and safe mode still prevents code from running.
- [On a host with no mise state yet, the trust query lets mise create its empty layout] → It records no loaded configuration and no trust, and an existing state stays unchanged.
- [Vale 3.25, markdownlint-cli2 0.24 or OpenSpec 1.15 change findings or behaviour] → The lane proves the refreshed supply on its own documents and Change before landing.
- [The GitLab supply image keeps the previous supply] → The GitLab plane is deferred, and its image moves when that plane is rebuilt.
