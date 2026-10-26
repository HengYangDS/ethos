# Design

## Context

See [proposal.md](proposal.md).

- **Two passes.** `_terminate_commands` first sends `SIGINT` to the group of every leader that `poll()` reports running, then closes every group with `_terminate_command` within one grace deadline.
- **Darwin's refusal.** A group whose members have exited but are not yet reaped refuses signals with `EPERM`. `_terminate_command` resolves that by probing the group until it is absent, within `_GROUP_REAPING_SECONDS`. A refusal that lasts, or a member that can still be signalled, still fails.
- **The race.** A leader can exit after `poll()` and before `killpg`. The interrupt pass then meets the same refusal, and it recorded the refusal as a failure before the close pass ran.

## Goals / Non-Goals

**Goals:**

- A leader that exits as it is interrupted does not fail cleanup when its group then closes within the bound.
- A command's own failure stays observable through cleanup.

**Non-Goals:**

- Changing the close pass, the bound or non-Darwin behavior.
- Ignoring a lasting refusal or a signalable member.

## Decisions

- **Re-check the leader on refusal.** On `PermissionError` in the interrupt pass, `poll()` decides:
  - If the leader has exited, the close pass owns the group, since it already resolves Darwin's unreaped members within its bound.
  - If the leader still runs, the refusal is recorded as before.
- **No new state.** The decision uses the leader's own exit status, which `Popen` already observes.

## Risks / Trade-offs

- [A group that refuses for another reason after its leader exited] → The close pass still raises once its bound passes, so the refusal stays a failure.
