# Design

## Context

See the [proposal](proposal.md). `repository_paradigm_report` returns `gaps[0].repair` as its next
action; the audit relays the first failing report's next action, and prove, land and publish relay
the audit's. `paradigm_repair_plan` dispatches each gap to a handler in `_HANDLERS` by obligation; a
gap without one is report-only. The repair command's preview already routes to the apply when it
plans edits, and otherwise to the first follow-up or report-only repair.

## Goals / Non-Goals

Goals:

- A refused proof names the repair preview whenever the product can write part of the repair.

Non-Goals:

- Evaluating the paradigm in `status` (`status-paradigm-gaps`), or changing any gap or its repair.

## Decisions

1. `repair.py` owns the routing, next to the plan it reads: `REPAIR_PREVIEW` is
   `ethos lane repair-paradigm --json`; `repair_next_action(plan)` returns the plan's first
   follow-up command, else its first report-only repair (the logic of the repair command's private
   `_first`, which goes); and `paradigm_next_action(root, gaps)` derives the plan and returns the
   preview when it holds edits, else `repair_next_action(plan)`, else the first gap's repair. The
   report calls it, so prove, land and publish inherit it.
2. Tests that asserted a deterministic gap's repair text as the report's next action now assert it
   on the gap and the preview as the next action; their intent, that the report names the canonical
   repair, is unchanged.

## Risks / Trade-offs

- A mixed report now names the preview instead of the judgment gap first; the preview names both
  and leads with the apply, so no gap is hidden.
