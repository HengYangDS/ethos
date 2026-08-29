---
name: ethos-skill-portfolio-governance
description: Use when creating, updating, routing, validating, projecting, or retiring ETHOS repo-local skills.
---

# ETHOS Skill Portfolio Governance

## When to Use

Use this skill when changing repo-local skills, activation metadata, package
manifests, projection drift controls, or the skill creation process.

## Workflow

1. Read `AGENTS.md`, `rules/skills.md`, and
   `docs/governance/playbooks-and-skills.md` before changing skill semantics.
2. Keep each skill narrow: trigger, workflow, evidence, and trust boundary.
   Route executable checks through `playbooks-v2`; put longer criteria in references.
3. Update `SKILL.md`, `package.toml`, and `activation.toml` together so the
   route, package digest, and command metadata remain aligned.
4. Require one owner for each subject-operation route. Retire an obsolete route
   with its reason, date, kill signal, and removal of its declared carrier.
5. Generate OpenSpec Skills and host-supported slash commands with the pinned
   official OpenSpec workflow; characterize the generated version and official
   status/instructions calls instead of copying templates into ETHOS.
6. Route tracked intent to official OpenSpec and durable proof to Attestations;
   source, tests, schemas, and docs retain their native authority. A skill must
   not create a shadow task store or lifecycle ledger.
   Treat matched evaluation as evidence, never task or progress state.
7. Run the current proof gate and changed-scope plan before claiming portfolio
   readiness.

## Evidence

```bash
uv run ethos prove --gate playbooks-v2 --json
uv run ethos plan --changed --json
```

## Trust Boundary

This skill governs skill projections only. Repository truth remains in source,
tests, schemas, docs, official OpenSpec, Attestations, and fresh ETHOS command
observations. Compiled Commitment values are transient inputs.
