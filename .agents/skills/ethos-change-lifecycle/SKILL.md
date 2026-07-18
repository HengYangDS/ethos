---
name: ethos-change-lifecycle
description: Use when driving an ETHOS change through status, plan, prove, land, publish, evidence, readiness, or accepted-root closeout.
---

# ETHOS Change Lifecycle

## When to Use

Use this skill when driving a repository change through the one canonical loop —
`status -> plan -> prove -> land -> publish` — or when checking readiness, compiling
a change plan, running proof, landing to the candidate role, or publishing. ETHOS
governs whether a change may land or publish, based on evidence, not assertion.

## Workflow

1. Run `ethos status --json`; confirm the checkout role (work_lane vs accepted_root)
   and read `required_gaps`. Never mutate an accepted root directly.
2. Run `ethos plan --changed --json` to compile the change plan: which rules match
   the changed paths, which gates are required, what evidence must exist.
3. After committing parity-relevant source changes, run `ethos parity gaps --json`.
   When it reports stale tracked parity, run `ethos parity shadow --adopter generic
   --target . --execute --write-evidence --json` **in the admitted Work Lane**, then
   commit the written evidence in that same lane. Candidate and accepted roots are
   intentionally write-protected, so parity cannot be deferred until after land.
4. Run `ethos prove --json` for readiness; `ethos prove --execute --expect-head
   "$(git rev-parse HEAD)" --json` for an EXECUTED proof. Dry-run readiness is not
   executed proof — only `--execute` produces trust-bearing, HEAD-bound evidence.
5. Run `ethos land --json`; the verdict gates the fast-forward to the candidate
   role. A blocked verdict refuses (non-zero exit); read `required_gaps`.
6. Run `ethos publish --json` for local publication readiness. Remote push is a
   deferred, separately human-authorized step — stop before it.

## Evidence

Use the `ethos ...` public command plane; the JSON is machine evidence:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
ethos land --json
ethos parity shadow --adopter generic --target . --execute --write-evidence --json
ethos report --json
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
