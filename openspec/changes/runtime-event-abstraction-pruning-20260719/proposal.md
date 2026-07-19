## Why

ETHOS currently carries two speculative mechanism families that do not own
product semantics: `lanes.py` reconstructs Runtime records only to forward calls
to lifecycle owners, while SQLite and workflow contracts describe event streams
with no production subscriber or reducer. These surfaces increase code, tests,
and indirection while obscuring the explicit governance chain.

## What Changes

- Make the lane CLI call lifecycle and retirement owners directly.
- Delete Runtime composition helpers and forwarding operations from `lanes.py`.
- Reuse the repository status lease projection instead of a second lease reader.
- Delete unused SQLite event and chronicle-event tables and CRUD functions.
- Delete workflow event declarations, models, validation, counts, schema fields,
  and tests that only self-prove an unimplemented stream.
- Delete all Runtime dependency containers and runtime parameters; tests patch
  the semantic owner module rather than injecting parallel object graphs.
- Delete ignored-state schema migration machinery and retired local database
  compatibility paths; disposable local state is recreated from current truth.
- Delete active standards-adapter declarations without production implementations
  or consumers.
- Keep Chronicle evidence, pure projections, Git hooks, explicit subprocess
  boundaries, and narrow one-to-one callables.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `adapters`: subject=explicit-lifecycle-owner-routing; reuse=extend;
  change=modify; facet:lifecycle=lane,retirement; facet:surface=cli,adapter;
  facet:authority=source,test. Adapter operations SHALL be called through their
  semantic owner without a parallel Runtime-composition facade.
- `kernel`: subject=event-abstraction-pruning; reuse=extend; change=modify;
  facet:lifecycle=workflow,state; facet:surface=contract,schema,store;
  facet:authority=source,test,schema. Event contracts SHALL survive only when
  backed by a producer, consumer or projection contract.

## Impact

- Lane CLI imports and mutation adapter layout.
- State-store initialization and tests.
- Workflow TOML, Pydantic contract, JSON Schema projection, and tests.

## Out Of Scope

- No DI container, service locator, event bus, Pluggy surface, compatibility
  re-export, alias, shim, dynamic extension loader, remote mutation, or change to
  lifecycle authority semantics.
