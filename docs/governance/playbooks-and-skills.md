---
subject: ethos:playbooks-skills
role: policy
state: canonical
relations:
  canonical_for: repo-local skill projection
---

# Repo-local Skills

Status: canonical.

Purpose: define `.agents/skills/` as the canonical repository-local skill
portfolio and keep skill procedures below repository truth.

See also: [Skill Rules](../../rules/skills.md) and
[Repo-local Skills](../../.agents/skills/README.md).

Skills route agents to current owner scripts, proof gates, rules, docs, and
repository facts. They do not create a task system, command plane, lifecycle
ledger, or source of truth. Each skill has one narrow subject, a manifest, and
an activation route.

The portfolio owner is responsible for structural validation:

```bash
.agents/skills/ethos-skill-portfolio-governance/scripts/portfolio_audit.py .
ethos prove --gate playbooks-v2 --json
ethos plan --changed --json
```

Repo-local skills must call current owner scripts or current proof gates. They
must not preserve removed command roots, copy policy into a shadow procedure,
or record durable task state outside tracked repository authority.

Host-native files are projections unless their host owns an official native
artifact. Repository source, tests, schemas, docs, OpenSpec, effective
Commitments, Attestations, and current command JSON remain authoritative.
