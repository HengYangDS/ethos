---
name: ethos-adoption-profile-governance
description: Use when applying ETHOS to another repository, changing its binding, capability projections, adapter boundaries, or cross-repository governance.
---

# ETHOS Adoption Binding Governance

## When to Use

Use this skill when ETHOS governs an external repository, changes its binding,
or evaluates its explicit profile and adapter boundaries.

## Workflow

1. Treat the governed subject as one Git repository; one typed profile binds its
   facts and proof depth without changing command semantics.
2. Run `uv run ethos adopt --root <repo> --json`, then inspect current facts with
   `uv run ethos status --root <repo> --json`.
3. Keep adopter skills, OpenSpec carriers, docs, evidence, and CI as thin
   projections over the same repository truth.
4. Preserve adapter boundaries: provider state belongs to the provider; durable
   truth must be promoted into source, tests, schemas, docs, OpenSpec, claims,
   or evidence.
5. Validate the adopter with the current full proof plan before claiming
   readiness.

## Evidence

```bash
uv run ethos adopt --root <repo> --json
uv run ethos status --root <repo> --json
uv run ethos prove --root <repo> --full --json
```

## Trust Boundary

Repository truth remains the source of truth. This skill routes adoption work;
it does not create a second task store or command plane. The adopter's tracked
files, profile, OpenSpec, claims, evidence, and ETHOS command JSON are the
truth. Hosted forges, CI providers, MCP, editor state, and generated assistant
surfaces remain adapters or projections.
