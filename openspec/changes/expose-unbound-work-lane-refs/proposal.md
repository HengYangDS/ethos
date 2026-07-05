## Why

Multi-agent repository work can leave a `work/*` branch ref after its linked
worktree is removed or after its semantics are absorbed by a later lane. That
ref is still a Git repository fact, but current status only reports linked
worktrees as Work Lane coordination state. Hidden unbound Work Lane refs make
small drift invisible during candidate integration.

## What Changes

- Extend workspace status so unbound configured Work Lane branch refs appear in
  `branch_bindings` as read-only Git facts.
- Extend coordination summary with an advisory unbound Work Lane ref count and
  gap without classifying unbound refs as active foreign worktrees.
- Keep closeout and conflict checks scoped to linked Work Lane worktrees where
  dirty paths and leases can be inspected safely.

## Capabilities

- `ethos-repository`: subject=workspace-status-work-lane-coordination; reuse=extend; change=modify; facet:lifecycle=runtime; facet:surface=cli; facet:authority=source
- `ethos-repository`: subject=workspace-status-contract; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=schema; facet:authority=schema
- `ethos-repository`: subject=repository-coordination-tests; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli; facet:authority=test

## Out Of Scope

- Deleting or retiring existing unbound Work Lane refs.
- Treating unbound refs as mutation-capable active lanes.
- Adding a second coordination store outside Git refs, leases, and status JSON.
