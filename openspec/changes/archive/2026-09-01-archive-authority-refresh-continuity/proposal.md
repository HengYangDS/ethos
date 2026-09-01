## Why

An authorized Work Lane base refresh rewrites the archive commit, while archive
recovery currently recognizes only the original effect `desired` commit as an
ancestor. The refreshed lane therefore loses its own archive authority and may
select an unrelated nearer archive, blocking post-archive proof with
`proof_archive_scope_stale`.

## What Changes

- Preserve one exact archive identity across an authorized Work Lane refresh by
  deriving the rewritten archive commit from existing Git and rebase evidence.
- Select an archive only when its Change identity and rewritten post-image match
  the current history; never fall back to a different archived Change.
- Add a regression covering archive, concurrent candidate advancement, refresh,
  and post-archive proof planning.
- Introduce no new persistent state, compatibility reader, lifecycle, or
  command.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: Archive authority remains exact and usable after an
  authorized Work Lane base refresh.

## Impact

The archive-transition reader and its focused tests change. Git history,
existing archive-effect and rebase Attestations, and official OpenSpec archive
artifacts remain the only evidence. The agent-entrypoint behavior and public
command surface do not expand.
