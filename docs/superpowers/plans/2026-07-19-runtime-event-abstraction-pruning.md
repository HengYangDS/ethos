# Runtime and Event Abstraction Pruning Implementation Plan

> Execute in the owned Work Lane only. Preserve one terminal design: no aliases,
> shims, wrappers, re-exports, DI container, event bus, or compatibility layer.

**Goal:** Delete non-semantic lane composition and unimplemented event surfaces
while preserving lifecycle authority, mutation safety, Chronicle evidence, and
pure projection behavior.

**Architecture:** CLI imports semantic owner operations directly. State schema
contains only consumed tables. Workflow contracts describe executable state
transitions rather than a speculative event stream. Deletion is preferred over
replacement abstraction.

## Task 1: Remove lane composition facade

**Files:**
- Modify `packages/ethos/src/ethos/surface/cli/lane/core.py`
- Modify `packages/ethos/src/ethos/adapters/mutation/lanes.py`
- Modify owner modules only where a canonical lease binding must be exposed
- Modify focused lane lifecycle/retirement tests

1. Add or adjust tests to assert CLI routes to lifecycle owners rather than facade forwards.
2. Run the focused tests and observe failure before production edits.
3. Import refresh and retirement operations from their owner modules in the CLI.
4. Delete `_call_refresh`, `_lane_refresh_runtime`, retirement Runtime factories,
   duplicate lease loading, and all matching forwarding operations from `lanes.py`.
5. Update tests to patch owner boundaries or use real temporary repositories.
6. Run Ruff and lane lifecycle/retirement tests; commit only when green.

## Task 2: Remove unused SQLite event logs

**Files:**
- Modify or delete `packages/ethos/src/ethos/adapters/store/state/events.py`
- Modify state initialization owner/imports
- Modify state-store tests

1. Add/adjust a test proving initialization creates only consumed tables.
2. Verify no production caller uses generic event CRUD.
3. Delete `_EVENT_TABLES`, event/chronicle-event table DDL and CRUD functions.
4. Move any surviving `initialize_state`/clock responsibility to its semantic owner
   instead of retaining an `events.py` shell.
5. Run Ruff and state-store tests; commit when green.

## Task 3: Remove workflow event stream declarations

**Files:**
- Modify `system/workflows.toml`
- Modify `packages/ethos-core/src/ethos_core/contracts/workflow.py`
- Modify generated/published workflow schema owner and tests
- Modify workflow contract and CLI payload tests

1. Change tests to assert absence of declaration-only event fields.
2. Delete `WorkflowEvent`, `WorkflowContract.event`, event validation/locality,
   event count, TOML `[[event]]` records and schema properties.
3. Regenerate the canonical schema using the repository owner command; do not hand-maintain a parallel schema.
4. Run Ruff, type checks, workflow tests and schema validation; commit when green.

## Task 4: Review, evidence, and local closeout

1. Check `git diff --check`, forbidden aliases/wrappers, production references,
   effective LOC delta, and Runtime/event entity counts.
2. Run Ponytail review and broad code review; fix all actionable findings.
3. Complete OpenSpec tasks and strict validation, then archive through the official lifecycle.
4. Refresh claims/parity only when the command plane reports stale evidence.
5. Run one HEAD-bound full proof; land to candidate; perform accepted closeout;
   retire the lane. Do not push any remote.
