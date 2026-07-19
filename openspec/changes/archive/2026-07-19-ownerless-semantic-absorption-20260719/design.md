## Context

The historical source has a tracked malformed `scope.toml`.  Normal scope
validation correctly refuses to use malformed declarations for coverage, but
that also prevents the only repair write.  Existing bootstrap is intentionally
for an absent, untracked companion and cannot safely cover this case.

## Goals / Non-Goals

**Goals:**

- Restore exactly the missing repair admission on the current candidate base.
- Keep malformed scope declarations non-authoritative.
- Record this as absorption of behavior, never historical topology.

**Non-Goals:**

- Accept a malformed scope, broaden a request, infer source-lane equivalence,
  or perform any source-lane retirement.

## Decisions

1. **Use a dedicated recovery state.** The reader returns
   `tracked_scope_repair_admitted` only for exactly one material path, exactly
   one selected invalid companion, and a Git-tracked target.  This differs from
   absent-companion bootstrap and does not add coverage.
2. **Keep the recovery in the shared scope reader.** Prewrite, changed planning,
   and proof already share this read model, so a side-channel exception would
   create authority drift.
3. **Test negative boundaries.** The regression proves unselected and widened
   requests remain uncovered.

## Risks / Trade-offs

- **Recovery becomes broad admission** -> require one path, one selected
  invalid companion, and exact Git tracking.
- **Historical package is mistaken for absorption** -> Chronicle and claim name
  the source head and current implementation separately; retirement is deferred.

## Migration Plan

1. Add the focused current-base regression and reader behavior.
2. Validate the active carrier, run focused proof, and record the current
   implementation HEAD after commit.
3. Archive, execute HEAD-bound proof, land, and close out through local ETHOS
   lifecycle commands.
4. Re-observe only the named source lane; use a later exact lifecycle decision
   if accepted proof and closeout establish absorption.
