---
name: ethos-repository-governance
description: Use when governing a repository with ETHOS commands, evidence, and adoption profiles.
---

# ETHOS Repository Governance

## When to Use

Use this skill when governing this repository with ETHOS commands, evidence,
OpenSpec records, adoption profiles, or proof gates.

## Workflow

1. Read `AGENTS.md` and the relevant canonical docs before changing governance
   behavior.
2. Run `ethos status --json` to classify checkout role, dirty state, and
   write-readiness gaps.
3. Route changed work through `ethos playbooks route --changed --json` or use
   `ethos plan --changed --json` for broader planning.
4. Run focused proof first; use `ethos report --json` before claiming
   readiness.
5. Keep repository source, tests, schemas, docs, OpenSpec records, claims,
   evidence, and command JSON above skill projections.

## Evidence

Use the `ethos ...` public command plane first:

```bash
ethos status --json
ethos plan --changed --json
ethos prove --json
ethos report --json
```

## Trust Boundary

This skill is a workflow package projection. Repository source, tests, schemas,
OpenSpec records, claims, evidence, and ETHOS command JSON remain the source of truth.
