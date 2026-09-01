# ETHOS Skills

Purpose: define the canonical repo-local skill source for ETHOS work.

Skills are narrow procedures over repository truth. They route agents to current
owner scripts, proof gates, rules, docs, schemas, OpenSpec, and evidence. They
do not create task state or replace repository authority.

## Operating Model

- Canonical tracked skills live under `.agents/skills/<skill-id>/`.
- Host-native skill directories are projections unless a host owns an official
  native artifact.
- Each governed skill has `SKILL.md`, `package.toml`, and an activation route.
- `activation.toml` is routing metadata, not authority over source, tests, docs,
  OpenSpec, or evidence.

## First-Glance Skill Routing

Start from the repository state, then select the smallest matching skill:

```bash
uv run ethos status --json
```

- Repository truth, adoption, proof, or Work Lane question:
  `ethos-repository-governance`.
- Skill portfolio, activation, package, or projection work:
  `ethos-skill-portfolio-governance`.
- Quality gates and owner scripts: `ethos-quality-gate-governance`.
- Governing another repository: `ethos-adoption-profile-governance`.

Foreign Work Lanes visible in command JSON are coordination signals, not write
authority. Skill procedures may observe them; they may not absorb, land, or
retire them without owner handoff or maintainer break-glass evidence.
