## Why

Archived OpenSpec paths currently encode a second date inside many logical
Change IDs, and the archive reader accepts identifiers that can start with a
number. This makes a historical directory date look like semantic identity and
permits recurring ambiguity rather than rejecting it at the normal workflow
boundary.

## What Changes

- Normalize every tracked archived carrier to
  `YYYY-MM-DD-<date-free-logical-change-id>` and repair all tracked references.
- Give the two historically distinct current-head adopter observations distinct
  logical IDs, so archive lookup remains exact rather than date-selected.
- Make active-ID, archive-name, archive-closeout, and archive-query validation
  reject numeric-leading and terminal-date logical IDs, plus duplicate logical
  archive identities.
- **BREAKING**: callers must use the date-free logical ID with
  `ethos openspec --archive-id`; obsolete dated logical-ID spellings have no
  alias, redirect, or fallback.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `command-plane`: subject=openspec-logical-change-identity; reuse=extend; change=modify; facet:lifecycle=authoring,validation,archive; facet:surface=openspec,cli,docs; facet:authority=source,openspec,claim,evidence. Define the canonical logical Change-ID and archive-query grammar.
- `repository-governance`: subject=openspec-archive-identity-closeout; reuse=extend; change=modify; facet:lifecycle=validation,archive,closeout; facet:surface=openspec,claims,chronicle; facet:authority=source,openspec,claim,evidence. Make archive identity canonical, unique, and fail-closed.

## Impact

OpenSpec archive paths and references, archive and active-ID validation,
regression tests, claims' `change_id` fields, and canonical OpenSpec guidance.
No private runtime store, foreign Work Lane, provider-specific mechanism, or
remote history rewrite is in scope.

## Out of Scope

- Dated Claim IDs, Chronicle paths, Git branch names, historical commit IDs, and
  remote-history rewrites.
- Any Codex-specific behavior, private JSONL/SQLite repair, foreign Work Lane
  mutation, or compatibility alias, redirect, symlink, and date-based fallback.
