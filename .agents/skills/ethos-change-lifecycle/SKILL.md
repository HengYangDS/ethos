---
name: ethos-change-lifecycle
description: Use when driving an ETHOS change through the public status, plan, prove, land, and publish commands.
---

# ETHOS Change Lifecycle

## When to Use

Use this skill for the public lifecycle loop
`status -> plan -> prove -> land -> publish`. ETHOS
governs whether a change may land or publish from evidence, not assertion.

## Workflow

1. Run `ethos status --json`; confirm the checkout role and read `required_gaps`.
   Never mutate an accepted root directly.
2. Run `ethos plan --changed --json` to compile the plan for the changed paths,
   required gates, and required evidence.
3. Run `ethos prove --json` for a dry-run check; run
   `ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json` for an
   executed proof. Only `--execute` produces HEAD-bound evidence.
4. Run `ethos land --json`; the verdict gates the fast-forward to the candidate
   role. A blocked verdict refuses (non-zero exit); read `required_gaps`.
5. Run `ethos publish --json` for local publication readiness. Remote push is a
   deferred, separately human-authorized step — stop before it.

## Evidence

Use the public `ethos` command plane; its JSON is machine evidence:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
ethos land --json
ethos status --json
```

Evidence boundaries (enforced in `system/evidence_boundaries.toml`): dry-run
readiness != executed proof; digest-bound != semantic correctness; local != hosted;
promotion != absolute correctness (only: a bounded claim was admitted).

## Bundled Resources

- `scripts/readiness.py` — deterministic read-only driver: runs status -> plan ->
  prove (readiness) in order, parses each verdict, prints the first blocking gap with
  its next action. Read-only; never lands, publishes, or executes proof. Run it
  before a land to see the whole readiness picture in one pass.
- `references/verdicts-and-gaps.md` — how to read the loop's JSON verdicts and act on
  common `required_gaps` (a skill-specific lookup not in the repository). Read it when
  a gap is unfamiliar.

## Trust Boundary

This skill is a workflow package projection. Repository truth — source, tests,
schemas, OpenSpec records, claims, evidence, and ETHOS command JSON — remains the
source of truth above any command output or skill text.
