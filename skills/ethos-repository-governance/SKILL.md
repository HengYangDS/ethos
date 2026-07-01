---
name: ethos-repository-governance
description: Use when governing ETHOS repository changes, proof, Work Lanes, rules, skills, docs, hooks, adoption, or release readiness.
---

# ETHOS Repository Governance

Use this skill for ETHOS repository governance work that touches rules, skills,
docs, OpenSpec records, proof, Work Lanes, hooks, adoption, or release
readiness.

## Required Pre-Reads

1. `AGENTS.md`
1. `rules/README.md`
1. `rules/mutation.md` before tracked writes.
1. `rules/hooks.md` when a task involves guard placement or bypasses.
1. `docs/architecture/terminal-governance-product-design.md` for terminal
   redesign work.

## Workflow

1. Run `ethos status --json` and confirm the checkout role.
1. For tracked writes, run `ethos lane prewrite <paths> --editor-root <worktree> --require-editor-root --json`.
1. Keep AGENTS as a thin pointer; put executable rules under `rules/`.
1. Keep canonical skills under `skills/`; treat host-native skill directories as
   projections.
1. Prefer focused proof, then run docs and report checks before claiming
   readiness.

## Evidence

Use command JSON as machine evidence:

```bash
ethos status --json
ethos quality docs-registry --json
ethos quality docs --json
ethos quality command-examples --json
ethos report --json
```

## Trust Boundary

This skill is a procedure over repository truth. Source, tests, schemas, docs,
OpenSpec, rules, and evidence remain higher authority.
