## Why

Multiple assistant agents can work in one Git repository at the same
time. ETHOS already surfaces foreign Work Lanes, but the status read model did
not make the current actor's authority explicit. Visibility without an explicit
capability boundary invites agents to treat another lane as cleanup residue and
retire or overwrite work they do not own.

## What Changes

- Extend `status.data.foreign_work_lanes[]` with an observe-only current actor
  capability read model.
- Keep communication/collaboration provider-neutral: Git worktree facts, leases,
  claim bindings, path scope, evidence, and status JSON are the shared substrate.
- Clarify product docs and accepted OpenSpec behavior: foreign lanes are
  observable by all agents, but write/land/retire authority stays with the owner,
  an accepted handoff, or maintainer break-glass evidence.
- Add regression tests and schema coverage for the new foreign-lane fields.

## Capabilities

- `ethos-repository`: subject=work-lane-collaboration-readmodel; reuse=extend; change=modify; facet:lifecycle=runtime,validation; facet:surface=cli,schema,docs,openspec,test; facet:authority=source,schema,docs,openspec,test
- `ethos-adapters`: subject=foreign-work-lane-projection; reuse=extend; change=modify; facet:lifecycle=runtime,validation; facet:surface=cli,openspec,test; facet:authority=source,openspec,test

## Out Of Scope

- No host-specific message bus for assistant hosts, MCP, IDEs, hosted forges, or CI providers.
- No new repository truth store.
- No automatic foreign lane handoff, closeout, deletion, or conflict resolution.
- No change to candidate integration's evidence and fast-forward arbitration.
