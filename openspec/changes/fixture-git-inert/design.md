# Design

## Context

See the [proposal](proposal.md). Git documents `maintenance.auto` as the switch that stops commands
from running `git maintenance run --auto` after their work.

## Goals / Non-Goals

Goals:

- A test repository's object storage changes only through the test's own commands.
- The settings that isolate test Git have one owner.

Non-Goals:

- Any change to how the product runs or configures Git.
- Changing what the gate-policy test proves; its loose-object precondition and diagnostic stay.

## Decisions

1. `tests/support/git_isolation.py` declares `GIT_ISOLATION`: `core.fsmonitor=false` and
   `maintenance.auto=false`.
2. The suite overlay in `tests/conftest.py` writes those entries before xdist starts its workers.
   The per-case fixture adds `init.templateDir` beside them.
3. The CLI runner keeps exactly the `GIT_ISOLATION` entries and `safe.directory` when it removes
   the test identity overlay.
4. A test commits through `init_git_repo` under a trace2 event target and asserts that no Git
   process ran `maintenance`. It fails before the overlay changes.

## Risks / Trade-offs

- If the repack had another cause, the gate-policy test can still fail. Its diagnostic then names
  the pack state, and that cause is not auto-maintenance.
- A product command that relies on auto-maintenance would differ under test. No product path does:
  the product never runs `gc`, `repack` or `maintenance`.
