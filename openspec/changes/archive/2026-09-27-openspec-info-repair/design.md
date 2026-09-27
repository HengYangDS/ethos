# Design

## Context

Official `validate --all --strict --json` can return exit zero and `valid: true` while naming canonical spec INFO issues. ETHOS currently keeps those issues as blocking repository obligations. Its existing repair selector handles `valid: false` specs only, so the same observation blocks the write needed to clear it.

## Goals / Non-Goals

- Admit only current validator-named canonical files for corrective prewrite under the existing Work Lane authority.
- Keep proof, commit, publication, and active-Change INFO behavior unchanged.
- Select an actionable status continuation.
- Do not add a second validator, warning waiver, durable state, or adopter-specific path.

## Decisions

Reuse the official validation-envelope parser for both gap reporting and repair derivation. Verify the exact INFO gap against one valid spec item and an existing regular canonical file. Compose this path into the existing repair scope, never into proof satisfaction. A request may repair one affected file at a time; demanding the entire finding set in one prewrite would make normal editor actions impossible. An unrelated path in the same request remains uncovered.

The selected active Change remains the sole intent source. If ordinary resolution is blocked solely by canonical INFO, status derives the first exact corrective prewrite command. Fresh validation after edits determines whether the obligation is cleared. The official active Change INFO rule remains informational and cannot bootstrap a repair path.

## Risks / Trade-offs

Repairability does not imply acceptance. A forged or stale issue must not mint write authority; tests cover envelope shape, matching gap, exact file type, mixed paths, and ordinary proof remaining blocked. The current strict treatment of canonical INFO is not redesigned in this bounded Change.
