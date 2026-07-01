---
subject: docs:start
role: workflow
state: active
relations:
  canonical_for: first run
---

# Quickstart

Status: active.

Purpose: give a first-run path for inspecting a repository, planning proof,
and understanding the mutation boundary.

See also: [Command Plane](../reference/command-plane.md) and
[Glossary](../reference/glossary.md).

Run the public command plane:

```bash
ethos status
ethos plan --changed
ethos prove
ethos land
ethos publish
```

Use `--json` for stable machine output.

First validation path:

```bash
ethos status --json
ethos prove --execute
ethos quality command-examples
```

For governance and discovery:

```bash
ethos doctor
ethos init --profile gitlab --dry-run
ethos adopt --profile gitlab --dry-run
ethos fleet inspect --target .
ethos playbooks check
ethos quality docs
ethos quality schemas
ethos quality gates
ethos quality provenance
ethos assistants doctor
ethos campaign hypotheses
```

Mutation defaults to dry-run/readiness. Apply paths require explicit
authorization and an expected HEAD.
