## Context

ETHOS owns the repository-local companion read model around official OpenSpec.
The official command remains responsible for archive movement and delta fusion.
After that movement, the final diff includes both ordinary material edits and
files beneath one dated archive, while the active Change is no longer selected.

## Goals / Non-Goals

**Goals:**

- Allow that one archive reconciliation to pass the same prewrite, plan, and
  proof scope reader.
- Keep archive authority tied to the current changed-path set.
- Fail closed for a missing or malformed archive companion.

**Non-Goals:**

- Do not make archived Changes permanent admission carriers.
- Do not modify the official OpenSpec schema or reimplement its archive logic.
- Do not relax claim binding, archive completeness, lane ownership, or remote
  publication requirements.

## Decisions

1. The reader inspects an archive only when at least one requested changed path
   is inside that archive directory. This makes current diff participation the
   sole selector, rather than archive age, name, or a claim reference.
2. A valid archive `scope.toml` can cover only requested material paths that it
   matches. A past archive not present in the current diff remains invisible.
3. Missing and malformed current archive companions emit explicit diagnostics
   and reduce to the existing carrier-invalid taxonomy. They never grant
   coverage.

## Risks / Trade-offs

- [Archive selection widens accidentally] → select only archives whose directory
  is already represented in the supplied changed-path set.
- [A broken companion masks an admission failure] → retain the stable uncovered
  path gap and add a carrier-invalid diagnostic.
- [Lifecycle divergence] → test the common reader directly; prewrite, changed
  plan, and prove already consume that reader.

## Migration Plan

No data migration is required. A valid archive scope companion already exists
beside every product-defined scope Change. The feature is exercised during the
DDWG archive-repoint commit, then normal proof and candidate-first landing
continue unchanged. Reverting the code restores the previous fail-closed state.
