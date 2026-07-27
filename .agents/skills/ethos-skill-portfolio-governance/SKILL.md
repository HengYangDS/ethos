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
   Put executable checks in its owner script and longer criteria in references.
3. Update `SKILL.md`, `package.toml`, and `activation.toml` together so the
   route, package digest, and command metadata remain aligned.
4. Route durable truth to source, tests, schemas, docs, OpenSpec, claims, or
   evidence; a skill must not create a shadow task store or lifecycle ledger.
5. Run the bundled owner script, current proof gate, and changed-scope plan
   before claiming portfolio readiness.

## Evidence

```bash
.agents/skills/ethos-skill-portfolio-governance/scripts/portfolio_audit.py .
uv run ethos prove --gate playbooks-v2 --json
uv run ethos plan --changed --json
```

## Trust Boundary

This skill governs skill projections only. Repository truth remains in source,
tests, schemas, docs, OpenSpec, claims, evidence, and ETHOS command JSON.
