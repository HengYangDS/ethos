---
subject: ethos:playbooks-skills
role: policy
state: canonical
relations:
  canonical_for: repo-local skill projection
---

# Playbooks And Skills

Repo-local skills are ETHOS playbook projections. They help agents choose the
right command, document, schema, or evidence path, but they do not become a new
source of truth.

The canonical local layout is:

```text
.agents/skills/
  README.md
  activation.toml
  <skill-id>/SKILL.md
```

`ethos playbooks check --json` validates the projection. `ethos playbooks route
--subject <subject> --json` selects matching playbooks from
`.agents/skills/activation.toml`.

Assistant host memory, local sessions, MCP servers, and vendor prompts remain
context providers or adapters. Durable guidance must be promoted into source,
tests, schemas, docs, OpenSpec records, claims, or evidence.
