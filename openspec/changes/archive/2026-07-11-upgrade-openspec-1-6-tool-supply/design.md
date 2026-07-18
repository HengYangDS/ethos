## Context

ETHOS delegates deep specification validation to the official OpenSpec CLI.
The local workstation already resolves version 1.6.0, but ETHOS-owned fallback
and bootstrap surfaces do not state the version that their proof relies on.

## Goals / Non-Goals

**Goals:**

- Make ETHOS-owned OpenSpec invocation reproducible at version 1.6.0.
- Preserve existing official CLI resolution precedence and strict validation.
- Prove the exact supply contract through focused tests and OpenSpec validation.

**Non-Goals:**

- Adding an ETHOS-specific OpenSpec parser, command plane, or vendor skill root.
- Altering historical evidence or hosted publication state.

## Decisions

- Pin only ETHOS-owned fallback, CI bootstrap, and scaffold invocations to
  `@fission-ai/openspec@1.6.0`; host launcher policy remains host-owned.
- Retain explicit `ETHOS_OPENSPEC_BIN`, cached official CLI, and PATH lookup
  precedence so contributors can supply a verified local executable.
- Use an added repository-governance requirement because the pin introduces a
  new deterministic-supply invariant without weakening existing governance.

## Risks / Trade-offs

- [A later official release exists] → explicit dependency refresh is required
  before ETHOS changes its declared tool supply.
- [A stale cache contains another CLI] → tests cover fallback only; explicit
  and cached precedence remain observable and do not silently rewrite pins.

## Migration Plan

1. Add pin assertions before changing runtime code and CI surfaces.
2. Replace owned package literals with `1.6.0`.
3. Run focused tests and official strict validation.
4. Revert the lane commit to roll back without touching host configuration.

## Open Questions

None.
