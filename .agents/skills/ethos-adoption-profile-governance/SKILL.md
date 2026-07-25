---
name: ethos-adoption-profile-governance
description: Use when applying ETHOS to another repository, changing its binding, capability projections, adapter boundaries, or cross-repository governance parity.
---

# ETHOS Adoption Binding Governance

## When to Use

Use this skill when ETHOS governs an external or adopted repository, changes
the repository binding or explicit capability projections, compares product and
adopter behavior, or checks whether repository governance remains isomorphic.

## Workflow

1. Treat the governed subject as a Git repository; one typed profile binds its
   facts and gates without changing command semantics.
2. Run `ethos status --json`, then `ethos adopt --root <repo> --json` or
   `ethos status --root <repo> --json` to expose the current boundary.
3. Keep adopter skills, OpenSpec carriers, docs, evidence, and CI as thin
   projections over the same kernel and transition commands.
4. Preserve adapter boundaries: provider state belongs to the provider; durable
   truth must be promoted into source, tests, schemas, docs, OpenSpec, claims,
   or evidence.
5. Validate the adopted repository with strict playbooks and repository-appropriate
   proof before claiming governance readiness.

## Evidence

Use the shared command plane for product and adopter repositories:

```bash
ethos adopt --root <repo> --json
ethos status --root <repo> --json
ethos playbooks check --root <repo> --mode v2-strict --json
ethos prove --root <repo> --json
```

## Trust Boundary

Repository truth remains the source of truth. This skill routes adoption work. The adopted repository's tracked files,
configured profile, OpenSpec records, evidence, claims, and ETHOS command JSON
are the truth. Hosted forges, CI providers, MCP, editor state, and generated
assistant surfaces remain adapters or projections.
