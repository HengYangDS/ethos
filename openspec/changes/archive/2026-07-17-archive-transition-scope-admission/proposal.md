## Why

The official OpenSpec archive command moves a completed Change before its final
claim repoint, archive files, and accepted-spec fusion can be committed. Current
ETHOS material-path admission selects only active or archiving Changes, so that
final reconciliation becomes uncovered and a repository hook correctly blocks
its own legal archive transition.

## What Changes

- Permit a valid archived Change companion to cover matching material paths only
  while a file from that same dated archive is part of the current Work Lane
  diff; its own archive directory is implicitly covered for that one transition.
- Preserve active and archiving Change selection as the ordinary admission
  path; an old archive remains unable to authorize later work.
- Classify an unusable current archive companion as carrier-invalid without
  granting coverage.
- Cover the transition with focused regression tests, official OpenSpec
  validation, and repository proof before archive.

## Capabilities

- `repository-governance`: subject=ethos:adopter-material-change-scope; reuse=extend; change=modify; facet:lifecycle=archive; facet:surface=openspec; facet:authority=source

## Out of Scope

- Changing official OpenSpec archive semantics or workflow schemas.
- Treating archived carriers as standing admission authority.
- Relaxing claim binding, archive completeness, Work Lane ownership, or remote publication proof.

## Impact

This changes the ETHOS material-scope reader, its invalid-state taxonomy, the
repository-governance contract, and focused tests. It does not change official
OpenSpec archive behavior, claim truth requirements, or remote publication.
