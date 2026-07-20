## Context

The current candidate contains 136 non-canonical archived carrier names:
134 have a terminal `-YYYYMMDD` segment in the logical portion and two repeat
the leading archive date. Removing that duplicate date produces one semantic
collision: the July 13 and July 14 adopter observations. Their proposals bind
different product contexts, so they receive explicit `current-product-head-...`
and `current-candidate-head-...` logical identifiers instead of an alias or
date-based lookup.

## Goals / Non-Goals

**Goals:**

- Keep one date in each archive path, before a date-free logical Change ID.
- Preserve every archived carrier's bytes except for path/reference migration
  and its logical-ID metadata where required.
- Move the failure upstream: identifier parsing, active selection, archive
  closeout, and query behavior all reject the invalid forms.
- Keep archive lookup exact-one and vendor-neutral.

**Non-Goals:**

- Renaming dated Claim IDs, Chronicle dates, Git branches, historical commits,
  private JSONL/SQLite state, or any foreign Work Lane.
- Adding a Codex-specific recovery mechanism, a compatibility alias, a
  redirect, symlink, or date-guessing reader.

## Decisions

1. **One grammar module.** Repository-level identifier helpers own the logical
   grammar and archive decomposition; adapters consume it, avoiding duplicated
   permissive regular expressions.
2. **Exact migration map.** Renames are deterministic from the observed archive
   name, with two explicit semantic disambiguations. Every tracked textual
   archive-path reference is rewritten atomically with the rename.
3. **Fail closed.** Any archive whose logical component ends in `-YYYYMMDD`,
   any numeric-leading active or query ID, and duplicate logical archive IDs
   blocks lifecycle closeout. The reader never recovers by choosing a date.
4. **Evidence identifiers remain distinct.** A Claim ID and Chronicle date are
   evidence labels, not OpenSpec Change IDs; they retain their historical date
   where that is their own identity.

## Risks / Trade-offs

- **A stale path reference is missed** -> rewrite only tracked text, then run
  a full old-path scan and lifecycle/claim gates before landing.
- **Two archives collapse accidentally** -> inspect all post-normalization
  logical IDs and require the archive-closeout uniqueness guard.
- **Candidate advances while proving** -> stop, record the stale boundary, and
  start a fresh successor; do not replay this lane.

## Migration Plan

1. Create this date-free active Change and bind its active Claim.
2. Rename the 136 observed archive directories and update their tracked path
   references plus affected claim `change_id` values.
3. Add grammar and closeout regressions, then run strict lifecycle, claims,
   parity, and executed proof on one committed HEAD.
4. Officially archive this Change, refresh the Claim's archive path and digest,
   repeat the proof on the archive HEAD, then use normal governed land and
   accepted closeout. Remote publication remains a separate transition.
