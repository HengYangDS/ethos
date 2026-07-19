## Context

The terminal architecture is a functional core with explicit imperative
adapters. Seven Runtime records and several event declarations were introduced
as test seams or anticipated extensibility, but the first high-impact slice can
remove the parallel facade and the event surfaces that have no runtime dataflow.

## Goals / Non-Goals

**Goals:**

- Reduce executable and test code while preserving lifecycle behavior.
- Make direct semantic ownership visible in imports and calls.
- Remove event entities with no producer, consumer, reducer, or durable authority.
- Leave a smaller base for subsequent Runtime-record elimination.

**Non-Goals:**

- No unified Runtime object, framework DI, event bus, plugin manager, wrapper,
  compatibility path, or new package.
- No weakening of pre-effect reobservation, CAS deletion, dirty fail-closed,
  proof, parity, claim, or closeout controls.

## Decisions

1. **Owner calls replace forwarding.** CLI functions import refresh and retirement
   operations from their owning modules. `lanes.py` retains only lane semantics
   it actually owns.
2. **No compatibility exports.** Deleted forwarding names are not re-exported.
3. **One lease projection.** Retirement consumes the existing status/binding
   lease owner rather than a second SQLite-only projection.
4. **Events require real flow.** Chronicle evidence remains a repository fact,
   but unused SQLite event logs and declaration-only workflow events are removed.
5. **No replacement abstraction.** Deletion is the replacement; a future event
   or plugin mechanism requires concrete independent producers/consumers and a
   separate admitted design.

## Risks / Trade-offs

- Tests may patch facade globals rather than semantic owners. They will be moved
  to owner-level behavior tests; no monkeypatch compatibility surface remains.
- A hidden consumer could rely on deleted SQLite functions. Full repository
  reference search and architecture tests must prove there is no production use.
- Workflow payload consumers may expect event fields. ETHOS is pre-stable and no
  compatibility was requested; schemas and tests converge atomically.

## Migration Plan

1. Add this OpenSpec carrier and implementation plan.
2. Delete lane facade forwarding and migrate tests/imports.
3. Delete unused state/workflow event surfaces and their self-referential tests.
4. Run focused quality/tests, strict OpenSpec validation, Ponytail review,
   parity/claim refresh when required, HEAD-bound proof, and local closeout.

## Open Questions

None. Reintroducing any extensibility mechanism requires new concrete demand.
