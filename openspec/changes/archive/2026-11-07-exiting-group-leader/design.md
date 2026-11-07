# Design

## Context

`_terminate_command` and the interrupt phase of `_terminate_commands` in
`src/ethos/adapters/process.py` treat `PermissionError` from `os.killpg` as Darwin's unreaped group
only when `process.poll()` already reports the leader exited, and otherwise raise it as a survivor.
XNU refuses signals to a process that is exiting before `waitpid` can collect it, so a leader in
that window reads as running and its refusal as a survivor.

## Goals / Non-Goals

Goals:

- An exiting leader's refusal resolves within the existing grace; a lasting refusal still fails.

Non-Goals:

- Changing the grace, the signal order or the containment limits the requirement already states.

## Decisions

1. **Wait for reapability, then reuse the exited-group path.** One helper polls the leader within
   `_GROUP_REAPING_GRACE_SECONDS` (0.5 seconds) and returns whether it became reapable; both call
   sites use it before deciding that a refusal is a survivor.
2. **Tests choose deterministically.** `test_gate_policy` sorts the two candidate blobs and, if the
   chosen blob is not loose, fails with `git count-objects -v` and the pack listing, so a recurrence
   names its cause; the sdist bound becomes 300 seconds, inside pytest's 600-second hang limit.

## Risks / Trade-offs

- A refusal now costs up to the grace before it fails; the grace already bounds the exited-group
  path, so the worst-case cleanup time is unchanged.
