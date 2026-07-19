## Why

IDE and agent hosts can leave detached temporary Git worktrees after a task or
probe ends. Existing ETHOS lane status focuses on governed `work/*` lanes, so a
clean detached temporary checkout can accumulate outside that coordination
count. Raw filesystem deletion is unsafe because other detached worktrees may
contain dirty recovery or semantic content.

## What Changes

- Add `ethos lane housekeeping` as a read-only inventory by default.
- Classify only clean, detached, unlocked worktrees below controlled temporary
  roots as removable.
- Require both explicit authorization and apply mode before removal.
- Recompute each candidate immediately before ordinary non-forced Git removal.
- Keep dirty, branch-bound, locked, recovery, and non-temporary worktrees
  protected with machine-readable reasons.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=detached-worktree-housekeeping;
  reuse=extend; change=modify; facet:lifecycle=inspection,retirement;
  facet:surface=cli,git,docs,openspec,test;
  facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- Work Lane branch or ref retirement.
- Dirty worktree preservation or semantic replay.
- Recovery-branch deletion.
- Remote publication or hosted-CI claims.
