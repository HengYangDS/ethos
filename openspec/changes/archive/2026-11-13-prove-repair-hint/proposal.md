# Proposal

## Why

A proof that the repository paradigm refuses names the first gap's canonical repair as its next
action, even when `ethos lane repair-paradigm` can write that repair and the rest. The newcomer
audit of 2026-11-12 shows the cost: a formed starter failed its first proof with 8 paradigm gaps, 7
of them repairable, and `next` named a hand edit. The paradigm report owns the next action that
prove, land and publish relay (`src/ethos/repository/paradigm/report.py:119`), and the repair plan
already knows which obligations it repairs (`src/ethos/repository/paradigm/repair.py:525`).

## What Changes

- When the repair would edit a carrier, the paradigm report's next action is the repair preview
  `ethos lane repair-paradigm --json`, whose own next action is the apply.
- Otherwise the next action is the repair's first follow-up command, else the first gap's canonical
  repair, as the repair command already chooses for its own preview.
- One function in `repair.py` makes that choice for both, and the repair command's private copy
  goes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: ADDED requirement `The paradigm routes a repairable gap to its repair`.

## Impact

`src/ethos/repository/paradigm/repair.py`, `src/ethos/repository/paradigm/report.py`, their tests,
and a CHANGELOG line.
