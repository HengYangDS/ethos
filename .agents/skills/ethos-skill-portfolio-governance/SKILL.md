---
name: ethos-skill-portfolio-governance
description: Use when creating, updating, routing, validating, projecting, or retiring ETHOS repo-local skills. Use this for meta-skill work, skill coverage, activation registry changes, package manifests, projection drift, and skill creator workflows.
---

# ETHOS Skill Portfolio Governance

## When to Use

Use this skill when the work changes repo-local skills, skill activation,
package manifests, provider projections, skill coverage, or the skill creation
process. It is the meta-skill for the skills portfolio; it does not replace
repository rules, docs, schemas, OpenSpec records, evidence, or command JSON as
repository truth.

## Workflow

1. Read `AGENTS.md`, `rules/skills.md`, and
   `docs/governance/playbooks-and-skills.md` before changing skill semantics.
2. Decide whether the repeated procedure truly needs a skill; otherwise update
   docs, rules, tests, or scripts instead.
3. Keep `SKILL.md` narrow: trigger, workflow, evidence, and trust boundary.
   Put longer explanation in `references/` and executable checks in `scripts/`.
4. Update `.agents/skills/activation.toml` and `package.toml` together so route
   metadata, included files, required sections, capabilities, and digests stay
   aligned.
5. Run `ethos playbooks check --mode v2-strict --json` and
   `ethos quality projection-drift --json` before claiming the projection is
   fresh.

## Evidence

Use these commands as machine evidence:

```bash
ethos playbooks check --mode v2-strict --json
ethos playbooks route --changed --json
ethos quality projection-drift --json
ethos prove --execute --gate playbooks-v2 --json
```

## Trust Boundary

This skill governs skill projections only. Repository source, tests, schemas,
current docs, OpenSpec records, claims, evidence, and ETHOS command JSON remain
the source of truth. Skills expose procedures; they do not create product truth.
