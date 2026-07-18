## Context

The 2026-07-16 accepted program permits exceptional resolution only after an
accepted Chronicle. The current local topology is not the old frozen snapshot:
there are 81 current rows, and Git-level re-observation separates 14 clean
absorbed frozen lanes, four absorbed dirty lanes, 33 frozen residual branches,
three valid leased frozen lanes, one diverged unbound ref, and 26 post-freeze
rows.

## Goals / Non-Goals

**Goals:**

- Bind later native decisions to one fresh matrix and explicit dispositions.
- Preserve dirty content and retain non-destructive blocks for unresolved work.
- Keep lane authority, candidate/accepted closeout, and remote publication
  distinct.

**Non-Goals:**

- Infer semantic supersession from branch names, timestamps, or an old record.
- Normalize missing leases by invention or modify foreign Work Lanes directly.
- Clear recovery packages or claim remote convergence.

## Decisions

1. **Matrix before exceptional action.** The matrix freezes branch/head/dirty
   observations and records their planned resolution. Native apply recomputes
   the same values and rejects stale decisions.
2. **Three disposition classes.** Clean accepted ancestors and the one
   patch-equivalent ref receive `retire`; absorbed dirty rows receive
   `preserve-retire`; unresolved, holder-bound, unbound, and post-freeze rows
   receive `block`.
3. **Existing command semantics stay canonical.** This change documents the
   existing Chronicle digest and disposition binding rather than adding a
   second resolver or a wildcard cleanup mechanism.
4. **Post-freeze lanes remain separately visible.** They are explicitly blocked
   in the matrix rather than silently added to the 2026-07-16 authority set.

## Risks / Trade-offs

- A concurrent target mutation makes its decision stale; the native resolver
  must reject it and the matrix is re-observed.
- `git cherry` patch equivalence is evidence for one specific clean ref, not a
  generic semantic equivalence algorithm.
- Blocking a residual lane is less satisfying than deletion but preserves
  evidence and prevents false completion.

## Rollback

The policy carrier can be reverted before land. After an exceptional resolution,
its native receipt and any preservation package remain the recovery record; no
raw ref rewrite is used for rollback.
