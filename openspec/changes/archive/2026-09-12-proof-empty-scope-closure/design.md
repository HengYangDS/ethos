## Context

See `proposal.md` for motivation. `CurrentScope` carries fresh `paths` and may
also carry an archive-effect authority resolved from historical OpenSpec state.
`proof_plan()` currently forwards that authority unconditionally to
`compile_plan()`. The proof contract then compares the authority's authorized
paths with fresh `changed_paths`; an empty fresh scope therefore fails against
unrelated historical paths.

## Goals / Non-Goals

**Goals:**

- Make an empty fresh scope compile as a no-op with respect to archive authority.
- Preserve existing fail-closed validation when a fresh non-empty scope is the
  subject of an archive effect.
- Establish a direct regression test at the proof-plan binding boundary.

**Non-Goals:**

- Do not delete, rewrite, or weaken historical archive effects or Attestations.
- Do not change OpenSpec archive lifecycle, current-scope resolution, gate
  selection, CLI shape, or accepted-root closeout semantics.

## Decisions

1. Gate forwarding of `CurrentScope.archive_authority` in `proof_plan()` on the
   effective fresh path tuple used to compile facts. This preserves the current
   archive validator and keeps the distinction at the single boundary where
   historical authority enters a current proof plan.
2. Test a `CurrentResolution` with an empty `CurrentScope` and valid-shaped
   archive authority, asserting that the compiled plan has no
   `openspec_archive` prior attestation and no archive-scope gap. Add a separate
   non-empty counterpart assertion so the repair cannot silently disable strict
   validation for live scope.
3. Do not alter `archive_scope_gaps()`: it remains the owner of validation once
   archive authority is applicable, avoiding a second interpretation of archive
   truth in the contract layer.

## Risks / Trade-offs

- [A malformed historic authority could be ignored when scope is empty] → That
  authority is not a current proof input; non-empty scopes continue to fail
  closed through the existing validator.
- [A broad condition could suppress validation for a live scope] → Bind the
  condition to the exact effective path tuple and test the non-empty stale-path
  case.
- [Historical archive semantics could be weakened] → Preserve all historical
  artifacts and keep the existing contract validator unchanged.

## Migration Plan

1. Add and observe the failing unit test for empty-scope archive forwarding.
2. Apply the smallest guarded forwarding change.
3. Run the focused unit test, official strict OpenSpec validation, and
   lane-local exact-HEAD full proof before considering any integration.
4. Revert by restoring unconditional forwarding if verification exposes a
   regression; no data migration or archive rewrite is involved.
