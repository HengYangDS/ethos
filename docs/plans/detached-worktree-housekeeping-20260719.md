---
subject: ethos:detached-worktree-housekeeping-20260719
role: plan
state: active
---

# Detached Worktree Housekeeping — 2026-07-19

## Goal

Make IDE and agent-created detached worktree residue visible and safely
removable without treating dirty, branch-bound, recovery, or product worktrees
as garbage.

## Contract

`ethos lane housekeeping` is read-only by default. It inventories linked Git
worktrees and marks a worktree removable only when all of these are true:

- it is detached from every branch;
- `git status --porcelain` is empty;
- its path is below a controlled temporary root (`$TMPDIR`, the system `/tmp`
  real path, or the current Codex home `worktrees` directory);
- it is not the current audited worktree.

Mutation requires both `--authorize` and `--apply`. The command uses ordinary
`git worktree remove` without `--force`, rechecks every target immediately
before removal, and reports protected entries with explicit reasons.

## Implementation

1. Add adapter-level inventory and removal behavior with injectable temporary
   roots for deterministic tests.
2. Add the public `ethos lane housekeeping` CLI surface.
3. Register the command in repository command truth and document the safety
   boundary.
4. Add unit and CLI contract tests before implementation.
5. Prove, land, and close out through the normal ETHOS lifecycle.

## Non-Goals

- No Work Lane branch or ref retirement.
- No deletion of dirty or missing-path worktrees.
- No cleanup of recovery branches or semantic source checkouts.
- No remote publication or hosted-CI claim.
