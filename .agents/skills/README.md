# ETHOS Skills

Purpose: define the canonical repo-local skill source for ETHOS work.

Skills are thin procedures over repository truth. They route agents toward
tracked commands, docs, schemas, OpenSpec records, rules, and evidence. They do
not replace those surfaces as authority.

## Operating Model

- Canonical tracked skills live under `.agents/skills/<skill-id>/`.
- Host-native skill directories are projections unless explicitly classified as
  official native artifacts.
- Each skill has `SKILL.md` with `name` and `description` frontmatter.
- Each skill has a `package.toml` manifest when the skill is part of the
  repository-governed portfolio.
- `activation.toml` maps paths and intents to candidate skills.
- Skills should be concise and point to rules or docs instead of copying them.

## Available Skills

| Skill | Use when |
| --- | --- |
| [ethos-repository-governance](ethos-repository-governance/SKILL.md) | Governing ETHOS repository changes, proof, Work Lanes, rules, skills, docs, or adoption. |
| [ethos-change-lifecycle](ethos-change-lifecycle/SKILL.md) | Driving a change through the main loop: status, plan, prove, land, publish. |

## Projection Boundary

Existing `.agents/skills` content is a host-facing projection until the terminal
projection generator replaces it. New semantic skill work belongs in `.agents/skills/`.
