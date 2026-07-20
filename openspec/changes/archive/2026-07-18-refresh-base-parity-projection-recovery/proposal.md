# Recover Governed Refresh from Valid Parity Projections

## Why

`ethos lane refresh-base` correctly treats a generated parity shadow conflict as
stale projection evidence rather than source truth. Git may retain a previously
validated resolution in index stage 0 while still reporting the path unmerged.
The current recovery path then overwrites that valid staged projection, so a
later replay can stop on unrelated historical conflict handling.

## What Changes

- Accept an already-staged parity shadow only when its JSON structure and adopter
  identity exactly match the conflicted path.
- Continue the sanctioned replay and require a fresh parity regeneration before
  proof; malformed or mismatched staged content remains source-conflict handling.
- Preserve fail-closed recovery for non-parity paths and all material source
  conflicts.

## Capabilities

- `repository-governance`: subject=work-lane-refresh-parity-projection; reuse=extend; change=modify; facet:lifecycle=mutation,validation; facet:surface=cli,hook; facet:authority=source,test,openspec,claim,evidence

## Impact

The change touches only refresh-base projection conflict classification and its
regression contract. It does not alter Git branch authority, candidate landing,
OpenSpec carrier semantics, or remote publication.

## Out Of Scope

- Auto-resolving source, test, config, OpenSpec, claim, or arbitrary JSON
  conflicts.
- Replacing the mandatory parity regeneration and HEAD-bound proof after replay.
- Pushing GitLab or GitHub, or modifying any foreign Work Lane.
