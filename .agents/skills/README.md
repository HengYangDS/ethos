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

## First-Glance Skill Routing

Always start from repository state, then select the smallest matching skill:

```bash
ethos status --json
ethos status --json
```

- Repository truth, adoption, proof, or Work Lane question: use
  `ethos-repository-governance`.
- Change lifecycle, readiness, land, publish, or closeout: use
  `ethos-change-lifecycle`.
- Skills, activation, meta-skills, projection drift, or skill creator work: use
  `ethos-skill-portfolio-governance`.
- CI, lint, format, type, docstring, coverage, or config gates: use
  `ethos-quality-gate-governance`.
- Governing another repository with the same kernel: use
  `ethos-adoption-profile-governance`.

Foreign Work Lanes visible in command JSON are coordination signals, not write
authority. Skill procedures may observe them; they may not absorb, land, or
retire them without owner handoff or maintainer break-glass evidence.

## Available Skills

| Skill | Use when |
| --- | --- |
| [ethos-repository-governance](ethos-repository-governance/SKILL.md) | Governing repository truth, authority boundaries, proof, Work Lanes, rules, docs, and adoption. |
| [ethos-change-lifecycle](ethos-change-lifecycle/SKILL.md) | Driving a change through the main loop: status, plan, prove, land, publish. |
| [ethos-skill-portfolio-governance](ethos-skill-portfolio-governance/SKILL.md) | Creating, updating, routing, validating, projecting, or retiring repo-local skills; includes the portfolio audit helper. |
| [ethos-quality-gate-governance](ethos-quality-gate-governance/SKILL.md) | Changing quality gates, CI, hooks, lint, format, types, docstrings, coverage, or config checks. |
| [ethos-adoption-profile-governance](ethos-adoption-profile-governance/SKILL.md) | Applying ETHOS to other repositories and keeping adoption profiles isomorphic with the product kernel. |

## Projection Boundary

Existing `.agents/skills` content is a host-facing projection until the terminal
projection generator replaces it. New semantic skill work belongs in `.agents/skills/`.
