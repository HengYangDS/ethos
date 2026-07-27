---
subject: ethos:agent-projections
role: explanation
state: canonical
relations:
  canonical_for: assistant and protocol surfaces
---

# Agent Projections

Status: canonical.

Purpose: define the boundary between repository truth and agent-facing
projections.

See also: [Repo-local Skills](../governance/playbooks-and-skills.md) and
[Command Plane](../reference/command-plane.md).

Assistant files, protocol adapters, hosted runners, provider prompts, and
repo-local skills may expose repository facts. None becomes a task, workflow,
or repository source of truth.

The canonical repo-local skill portfolio lives in `.agents/skills/`. Its
integrity is checked by the portfolio owner and the current proof gate:

```bash
.agents/skills/ethos-skill-portfolio-governance/scripts/portfolio_audit.py .
ethos prove --gate playbooks-v2 --json
```

Agent protocols are optional adapter boundaries, not a public lifecycle. A
projection may read and format repository facts; durable results must be
promoted into source, tests, schemas, docs, OpenSpec, or evidence before they can
support a claim.
