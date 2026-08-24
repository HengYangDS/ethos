## Context

See `proposal.md`. Runtime bytes already live under `<git-common-dir>/ethos/runtime/<digest>`, while each generated hook currently embeds that digest in its own relative Python path. Observation and garbage collection recover runtime identity by parsing launcher text. Repair and proof remediation render ambient `ethos` commands, so an intact stale launcher can become both the blocker and the only available interpreter of the blocker.

## Goals / Non-Goals

**Goals:**

- One fail-closed runtime selection owner inside the existing repository runtime semantic package.
- Validate before activation and make selection plus hook activation observable as one transition.
- Derive hook execution, diagnosis, repair, proof remediation, and garbage-collection retention from the selected runtime.
- Delete launcher-text runtime discovery and ambient command rendering.

**Non-Goals:**

- A second runtime registry, daemon, update channel, package resolver, or compatibility reader.
- Automatic network installation, adopter-specific policy, or weakening proof admission.
- General maintainer break-glass; this atom only makes the normal proof/repair route executable.

## Decisions

### `CURRENT` is a narrow immutable-runtime selector

`<git-common-dir>/ethos/runtime/CURRENT` contains one canonical runtime digest plus a terminating newline. The owner validates shape, containment, directory identity, manifest, runtime files, and expected source identity before returning an executable. A symlink, extra content, invalid digest, or invalid target fails closed.

Alternative rejected: derive the selected runtime from launcher text. That duplicates authority into every hook and makes a stale hook define its own repair runtime.

### Hooks resolve `CURRENT` at execution time

Generated launchers contain one common relative selector path, not a runtime digest. Their generation digest therefore represents hook semantics only; runtime replacement does not manufacture another semantic launcher format. The Python owner validates that launcher projection against the selected runtime.

Alternative rejected: rewrite launchers with every runtime digest. This preserves the current direct-runtime incumbent and requires reverse parsing for observation and cleanup.

### Activation stages, validates, then switches

Installation materializes and validates the immutable runtime and complete hook generation first. It then atomically replaces `CURRENT`, activates common `core.hooksPath`, clears worktree overrides, and post-observes the exact binding. On failure it restores both selector bytes and Git configuration before cleanup.

Alternative rejected: select the runtime before hooks validate. That exposes a partially activated package authority.

### Executable commands come from the selected runtime

A single command renderer returns the selected runtime's absolute `ethos` entrypoint invocation with explicit `--root` and, for proof, `--expect-head`. Hook reports and status repair actions consume it; no consumer renders `ethos ...` independently.

Alternative rejected: use `PATH`, `uv run`, or source checkout prefixes. These are unavailable in package-only adopters and create multiple command authorities.

### Garbage collection treats `CURRENT` as the runtime consumer

The selector is the sole active runtime consumer. Effective hook config, live process commands, and in-flight operations remain consumers of hook generations or historical runtimes during bounded execution. Unknown consumer state blocks cleanup.

## Risks / Trade-offs

- [Selector replacement and Git config activation cannot be one filesystem primitive] → preserve exact prior selector and config, restore both on any failed validation, then post-observe.
- [A deleted selected runtime makes every hook unavailable] → fail closed with a selector/runtime diagnostic; installation never deletes the selected target.
- [A mutable text file could redirect execution] → accept only a canonical digest and validate the content-addressed target and manifest before execution.

## Migration Plan

1. Install and validate the new immutable runtime and digest-independent hooks.
2. Atomically write `CURRENT`, activate common hooks, and post-observe all linked worktrees.
3. Remove legacy direct-runtime hook generations and unselected runtime directories only after consumer inventory proves them unused.
4. Re-running installation is idempotent and retains the same selected runtime and hook generation.
5. On activation failure, restore prior selector bytes and Git config; do not clean either the prior selected runtime or prior active hooks.
