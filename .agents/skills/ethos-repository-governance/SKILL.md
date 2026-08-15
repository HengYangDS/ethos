---
name: ethos-repository-governance
description: Use when governing a repository with ETHOS commands, evidence, and adoption profiles.
---

# ETHOS Repository Governance

## When to Use

Use this skill when governing repository truth, authority boundaries, proof,
Work Lanes, OpenSpec consumption, or adoption profiles.

## Workflow

1. Read `AGENTS.md` and the relevant canonical docs before changing governance
   behavior.
2. Run `uv run ethos status --json` to classify checkout role, dirty state, and
   write-readiness gaps.
3. Run `uv run ethos plan --changed --json` to compile the changed-scope gates
   and evidence requirements.
4. Run the relevant `uv run ethos prove --gate <gate-id> --json` command first;
   use `uv run ethos prove --full --json` when the full local proof plan is
   required.
5. Keep source, tests, schemas, docs, OpenSpec, Commitments, Attestations, and command
   JSON above skill projections.

## Evidence

Use the current public command plane or the bundled owner script:

```bash
.agents/skills/ethos-repository-governance/scripts/govern_check.py --root .
uv run ethos status --json
uv run ethos plan --changed --json
uv run ethos prove --json
```

## Bundled Resources

- `scripts/govern_check.py` — deterministic read-only status -> plan -> prove
  readiness summary. It never lands, publishes, or executes proof.
- `references/governance-map.md` — a compact map from governance concern to its
  current owner.

## Trust Boundary

This skill is a workflow package projection. Repository source, tests, schemas,
OpenSpec records, Commitments, Attestations, and ETHOS command JSON remain the source of
truth.
