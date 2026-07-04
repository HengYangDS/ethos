---
name: ethos-change-lifecycle
description: Use when driving an ETHOS repository change through its main loop — status, plan, prove, land, publish — or when a user asks how to check readiness, compile a change plan, run proof, land a change, or publish. Use this whenever work touches the status/plan/prove/land/publish commands, evidence, or the accepted-root promotion path, even if the user does not name ETHOS explicitly.
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
3. Run `ethos prove --json` for readiness; `ethos prove --execute --expect-head
   "$(git rev-parse HEAD)" --json` for an EXECUTED proof. Dry-run readiness is not
   executed proof — only `--execute` produces trust-bearing, HEAD-bound evidence.
4. Run `ethos land --json`; the verdict gates the fast-forward to the candidate
   role. A blocked verdict refuses (non-zero exit); read `required_gaps`.
5. Run `ethos publish --json` for local publication readiness. Remote push is a
   deferred, separately human-authorized step — stop before it.

## Evidence

Use the `ethos ...` public command plane; the JSON is machine evidence:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
ethos land --json
ethos report --json
```

Evidence boundaries (enforced in `system/evidence_boundaries.toml`): dry-run
readiness != executed proof; digest-bound != semantic correctness; local != hosted;
promotion != absolute correctness (only: a bounded claim was admitted).

## Trust Boundary

This skill is a workflow package projection. Repository truth — source, tests,
schemas, OpenSpec records, claims, evidence, and ETHOS command JSON — remains the
source of truth above any command output or skill text.
