# Agent Entry Point

ETHOS is governed through the repository source, tests, schemas, docs, and
command plane.

## Authority

1. User instruction.
1. Source code, tests, schemas, and package metadata.
1. Canonical docs under `docs/concepts/`, `docs/architecture/`, and
   `docs/governance/`.
1. Evidence under `docs/evidence/`.
1. Archive material under `docs/archive/`.

## Operating Rules

- Use `ethos ...` as the only public command vocabulary.
- Treat assistant, MCP, ACP, hosted CI, and external workflow runtimes as
  projections or adapters, not truth stores.
- Keep product behavior inside `packages/ethos-*`; do not create `tools/`
  product behavior.
- Keep profile-specific semantics in profiles or adopter repositories.
- Write tests for behavior changes.
- Do not turn local state under `.ethos/state/` into tracked truth.
