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
2. Preview `uv run ethos adopt --root <repo> --json` only for an unadopted
   repository. Review the profile and official OpenSpec config; preserve its
   existing layout. Follow the current result rather than a fixed pipeline.
3. Keep adopter skills, OpenSpec carriers, docs, Attestations, and CI as thin
   projections over the same repository truth.
4. Preserve adapter boundaries: provider state belongs to the provider; tracked
   intent goes to official OpenSpec and durable proof goes to Attestations while
   source, tests, schemas, and docs retain their native authority.
5. Distinguish binding, readiness and executed proof. A completed observation
   needs no repeated read; binding alone certifies neither historical commits
   nor full scaffold, migration, uninstall or crash-atomic file updates.

## Evidence

Select only the command needed by the current boundary; these are not a pipeline.

```bash
uv run ethos adopt --root <repo> --json
uv run ethos status --root <repo> --json
uv run ethos prove --root <repo> --execute --full --expect-head <exact-head> --json
```

## Trust Boundary

Repository truth remains the source of truth. This skill routes adoption work;
it does not create a second task store or command plane. The adopter's tracked
files, profile, official OpenSpec, Attestations, and fresh ETHOS observations are
the truth inputs and durable results. Commitment is compiled transiently.
Hosted forges, CI providers, MCP, editor state, and generated assistant surfaces
remain adapters or projections.
