---
name: ethos-repository-governance
description: Use when governing a repository with ETHOS commands, evidence, and adoption profiles.
---

# ETHOS Repository Governance

## When to Use

Use this skill when governing repository truth, authority boundaries, proof,
Work Lanes, OpenSpec consumption, or adoption profiles.

## Workflow

1. Read `AGENTS.md`, then run `ethos status --json` in the target worktree.
2. Read the result's `verdict`, `required_gaps`, singular `next_action`,
   `continuation`, and `user_decision_required`; follow that result rather than
   a remembered sequence.
3. Load only the rule, OpenSpec Change, design document, or focused gate needed
   for the current action.
4. Before tracked mutation, obtain a passing `ethos lane prewrite` decision for
   the exact target root and paths.
5. Keep source, tests, schemas, docs, official OpenSpec, Attestations, and fresh
   command observations above skill projections. Commitment is transient
   compilation, not another truth store.

## Evidence

Use the current public command plane:

```bash
ethos status --json
```

## Bundled Resources

- `references/governance-map.md` — a compact map from governance concern to its
  current owner.

## Trust Boundary

This skill is a workflow package projection. Repository source, tests, schemas,
official OpenSpec records, Attestations, and fresh ETHOS command observations
remain above it.
