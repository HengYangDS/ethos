# Proposal

## Why

Git runs the reference-transaction hook once for each state of a transaction: preparing, prepared, committed and aborted. ETHOS governs only the prepared state, yet the generated launcher starts the selected runtime's Python for every state. A probe with Git 2.56.0 found three hook invocations for each `git update-ref` and about seven for each `git commit`, of which one and two are prepared. Each needless start costs about 0.13 s (interpreter start, the Git adapter imports and the repository root lookup), against no measurable time for a shell `exit 0`. Every adopter pays this on every ref update and commit, and our heavy tests pay it through their fixture hooks.

The other states cannot change Git's outcome. Git ignores the hook's exit status for committed and aborted: a probe hook that exited 9 in committed still let `update-ref` succeed. ETHOS's protocol answers preparing with `phase_not_governed` and committed or aborted with a pass report, and it records nothing. ETHOS's own ref effects claim their intents in the executor, not in the hook.

## What Changes

- **Declared states.** The package hook declaration names the states each hook governs. Reference-transaction governs only `prepared`.
- **Launcher guard.** The launcher generated from that declaration exits successfully, in plain POSIX `sh`, for any other state before it reads the runtime selection.
- **One rule in the protocol.** The protocol treats every state other than prepared as not governed and drops its separate committed and aborted branch. A launcher from an earlier runtime that still sends those states gets a pass.
- **Compatibility.** A declaration without states stays valid, so the launchers of an earlier selected runtime stay current until their repository reinstalls hooks. Adopters get the new launcher when they rebind with `ethos hook install`.
- **Specs.** quality restates the two hook requirements as "only prepared is governed" and adds the launcher requirement.
- **CHANGELOG.** One entry under `[Unreleased]`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `quality`: hook launchers start the runtime only for governed states.

## Impact

- One `git update-ref` starts the runtime once instead of three times, and one commit twice instead of about seven times.
- `ethos hook ref-transaction --phase`, the interactive single-update command, keeps its own phase handling.
- Product Python stays within its ceiling: the declaration check grows by a few lines, and the protocol loses its terminal branch.
