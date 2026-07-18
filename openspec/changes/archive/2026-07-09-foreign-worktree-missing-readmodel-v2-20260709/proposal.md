# Foreign Worktree Missing Read Model

## Why

In multi-agent work, a Git worktree registry entry can outlive the physical
worktree path when a host, agent, or manual cleanup removes the directory before
Git metadata is pruned. That is a small but decisive coordination signal. ETHOS
status and closeout readers must make the state visible instead of crashing or
silently granting cleanup authority.

## What Changes

- `worktree_binding` gains the physical-path state `missing` for Git worktree
  registry entries whose path no longer exists.
- Candidate read-model bindings explicitly distinguish `absent` (configured
  candidate branch not created), `unbound` (branch exists without a candidate
  worktree), and `missing` (registered candidate worktree path disappeared)
  while actual worktree entries remain physical bindings only.
- Foreign Work Lane readers treat a missing physical path as unobservable dirty
  state: `dirty=false`, `dirty_paths=[]`, and coordination remains advisory for
  accepted-root readers.
- Workspace-status schema and regression tests cover the missing-path payload.

## Capabilities

- `repository-governance`: subject=foreign-worktree-missing-readmodel; reuse=extend; change=modify; facet:lifecycle=runtime,validation; facet:surface=cli,schema,openspec,test; facet:authority=source,schema,test,openspec

## Out Of Scope

- No new worktree registry, lease store, or truth center.
- No automatic cleanup, pruning, retirement, handoff, or branch deletion.
- No mutation authority over the missing foreign Work Lane.
- No claim that hosted forge or CI state is available.
