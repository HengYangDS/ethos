---
subject: ethos:detached-worktree-housekeeping-20260719
role: plan
state: superseded
relations:
  implements: detached-worktree-housekeeping-20260719
  see_also: docs/reference/command-plane.md, openspec/specs/repository-governance/spec.md
  superseded_by: ethos:terminal-governance-product-design
---

# Detached Worktree Housekeeping — 2026-07-19

Status: active implementation; local lifecycle closeout is in progress.

Purpose: define the fail-closed inventory and cleanup boundary for detached
temporary Git worktrees without discarding dirty or semantically valuable state.

See also: [Command Plane](../reference/command-plane.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Repository Governance Specification](../../openspec/specs/repository-governance/spec.md).

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
  real path, or an explicit `$ETHOS_HOUSEKEEPING_ROOTS` entry);
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
