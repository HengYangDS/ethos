## Context

ETHOS had written Work Lane discipline into governance language, but the product
runtime did not enforce it. The workspace state schema already contained
`leases`, yet status, mutation, and CLI admission paths did not consume lane
roles or lease acquisition. This allowed agents to rely on memory and raw git
commands instead of a public command-plane guard.

The product must protect three boundaries:

- accepted roots, candidate roots, submit branches, detached roots, and unknown
  roots are protected from tracked writes;
- foreign `work/*` lanes are observable through git metadata but must not be
  entered, read, closed, cleaned, or mutated by an unassigned agent;
- local lease state coordinates a checkout, but it is ignored runtime state and
  not durable repository truth.

## Goals / Non-Goals

**Goals:**

- Make lane topology visible through `ethos status` and `ethos lane status`.
- Add a `prewrite` admission command that tools can call before tracked
  mutations.
- Add a lane-start command that creates `work/*` lanes from a clean accepted
  root and records leases in ignored SQLite state.
- Block `land --apply` and `publish --apply` outside owned Work Lanes before
  product self-audit runs.

**Non-Goals:**

- Do not inspect foreign lane file contents.
- Do not replace durable evidence with SQLite leases.
- Do not implement remote publication or branch cleanup in this change.

## Decisions

### Use git worktree metadata for foreign lane discovery

`git worktree list --porcelain` provides path, branch, and head without reading
foreign worktree contents. ETHOS classifies branches into roles and reports
foreign `work/*` lanes as `foreign_work_lane_present`.

Alternative considered: walking sibling directories. That would risk touching
unassigned checkouts and would be less authoritative than git metadata.

### Make prewrite a first-class lane command

`ethos lane prewrite` checks target paths, role, and editor-root binding before
editing. This gives JetBrains, CLI agents, and future MCP/ACP adapters a stable
admission point instead of relying on prose rules.

Alternative considered: only checking inside `land` and `publish`. That is too
late for normal file edits and does not protect against direct patch/write
tools.

### Store leases in ignored local SQLite state

Lane start records lease rows in `.ethos/state/state.sqlite`. This supports
local coordination while preserving the rule that repository truth remains in
source, tests, schemas, specs, docs, claims, and evidence.

Alternative considered: committing lease files. That would leak host-local
state into durable truth and create avoidable merge churn.

### Evaluate apply admission before self-audit

Apply-mode `land` and `publish` now compute mutation admission before product
self-audit. A protected-root request must return a structured admission failure
even when the target repo is only an adopter or test repo without ETHOS product
schemas.

Alternative considered: making self-audit tolerant of every non-product repo.
That is broader adopter-design work and should not be required for mutation
blocking to work.

## Risks / Trade-offs

- Foreign lane presence is currently a required gap, not an ownership transfer
  protocol. Mitigation: future lane lease ownership can add explicit assignment
  and handoff semantics.
- `prewrite` treats non-ignored paths as tracked candidates. Mitigation: this is
  conservative; protected roots should not be modified without a Work Lane even
  for newly created tracked files.
- Leases can expire or be stale. Mitigation: leases are advisory coordination
  facts; git branch/worktree role remains the mutation gate.

## Migration Plan

1. Land the command-plane admission behavior with focused tests.
2. Require agents and adapters to call `ethos lane prewrite` before tracked
   writes.
3. Extend future lane lifecycle work with explicit lease release, handoff, and
   stale-lease diagnostics.

Rollback is a normal git revert of this change. Since lease state is ignored
local runtime data, no repository data migration is required.

## Open Questions

- Should ETHOS introduce signed lane lease ownership for multi-agent hosts?
- Should foreign lane gaps distinguish `present`, `assigned_to_other`, and
  `stale` states?
