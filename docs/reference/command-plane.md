---
subject: ethos:command-plane
role: reference
state: canonical
relations:
  canonical_for: public commands
---

# Command Plane

Public daily commands:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

Advanced commands remain under `ethos ...`. Retired root commands are not
compatibility surfaces.

Quality and governance:

```bash
ethos quality command-registry
ethos quality command-surface
ethos quality claims
ethos quality docs-registry
ethos quality provenance
ethos quality standards
ethos self audit
ethos self hypothesize
ethos campaign hypotheses
ethos report
```

Agent projections:

```bash
ethos assistants doctor
ethos assistants check-projections
ethos assistants mcp-manifest
```

Mutation readiness is explicit:

```bash
ethos land --apply --authorize --expect-head <git-head>
ethos publish --apply --authorize --expect-head <git-head>
```

Those commands still report readiness in the current implementation; remote
publication remains an adapter responsibility.
