## Why

Stash hides dirty work outside the repository truth surfaces that ETHOS can
inspect, claim, and close out. In a multi-agent repository this makes residue
look safe while it is merely invisible: another agent cannot know whether the hidden stack is a half-change or
stale pollution from a protected root.

ETHOS therefore needs an explicit repository rule and hook-level signal:
classified dirty work is either absorbed into an owned Work Lane or reverted
from the protected root. `git stash` is forbidden as a handoff, backup, or closeout carrier.

## What Changes

- Add repository-governance requirements for stashless residue closeout and
  protected-root pollution classification.
- Make pre-run hook admission block stash mutation commands with
  `git_stash_forbidden`, while allowing observation-only stash reads.
- Update repository hygiene so tracked text cannot reintroduce positive stash
  guidance.
- Replace stale tracked planning prose that recommended hidden diff evidence.

## Capabilities

- `repository-governance`: subject=stashless-residue-closeout; reuse=extend;
  change=modify; facet:lifecycle=authoring,validation,closeout;
  facet:surface=rules,hook,ci,skill; facet:authority=source,test,openspec,evidence

## Out Of Scope

- No new truth store, lane role, or backup subsystem.
- No prohibition on observation-only forensics via `git stash list` or
  `git stash show`.
