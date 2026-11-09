# Design

## Context

`predecessor_policy_gaps` runs the installed runtime's `prove --full` without `--execute`, which
plans every gate and audits the repository, and bounds it with `seconds("tool")`. The declared
deadlines are `tool` 60 s for one tool call and `gate` 600 s for one gate's run.

## Goals / Non-Goals

Goals: let landing's predecessor probe finish under host load, still bounded.

Non-Goals: making the plan cheaper; a new deadline parameter; the probe's comparison.

## Decisions

1. **The probe is bounded like a gate.** A full plan does a gate's work, not one tool call's, so
   `seconds("gate")` bounds it. A repository that lowers `timeout.gate_seconds` lowers the probe's
   bound with it.

## Risks / Trade-offs

- A hung predecessor holds a landing for up to the gate deadline before it refuses.
