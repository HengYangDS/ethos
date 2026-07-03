---
name: ethos-change-lifecycle
description: Use when driving an ETHOS repository change through its main loop — status, plan, prove, land, publish — or when a user asks how to check readiness, compile a change plan, run proof, land a change, or publish. Use this whenever work touches the status/plan/prove/land/publish commands, evidence, or the accepted-root promotion path, even if the user does not name ETHOS explicitly.
---

# ETHOS Change Lifecycle

Drive a repository change through the one canonical loop. ETHOS governs whether a
change may land or publish, based on evidence — not on assertion. This skill is the
daily driver for that loop.

```text
status -> plan -> prove -> land -> publish
```

Each step is a command that emits a JSON decision (`ok`, `state`, `required_gaps`,
`next_actions`). Read the decision; do not assume success.

## Required Pre-Reads

1. `AGENTS.md` — authority order and operating kernel.
2. `rules/mutation.md` — before any tracked write.
3. `system/tao.md` — the value judgment layer, when a call is ambiguous.

## Workflow

1. **status** — `ethos status --json`. Confirm the checkout role (work_lane vs
   accepted_root) and read `required_gaps`. Never mutate an accepted root directly.
2. **plan** — `ethos plan --changed --json`. Compile the change plan: which rules
   match the changed paths, which gates are required, what evidence must exist.
3. **prove** — `ethos prove --json` for readiness; `ethos prove --execute
   --expect-head "$(git rev-parse HEAD)" --json` for an EXECUTED proof. Dry-run
   readiness is NOT executed proof — only `--execute` produces a trust-bearing
   proof (see the evidence boundaries below).
4. **land** — `ethos land --json`. Lands the work lane to the candidate role; the
   verdict gates the fast-forward. A blocked verdict refuses; read `required_gaps`.
5. **publish** — `ethos publish --json`. Local publication readiness. Remote push
   is a deferred, separate, human-authorized step — stop before it.

`ethos report --json` is the read-only scorecard across all governed checks; use it
to see the whole picture without mutating.

## Evidence Boundaries (do not conflate)

These are enforced in `system/evidence_boundaries.toml`. The left never implies the
right:

- dry-run readiness != executed proof
- digest-bound evidence != semantic correctness
- local evidence != hosted verification
- promotion != absolute correctness (only: a bounded claim was admitted)

## Decision Contract

Every command emits one verdict shape: `ok` + `state` + `required_gaps` +
`next_actions`. When `ok` is false, the `required_gaps` name exactly what blocks the
change and `next_actions` name the next command. Follow the next action; do not
work around the gap.

## Trust Boundary

This skill is a procedure over repository truth. Source, tests, schemas, docs,
OpenSpec, rules, and evidence remain higher authority than any command output.
