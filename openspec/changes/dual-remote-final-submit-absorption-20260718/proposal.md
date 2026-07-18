## Why

Two configured remote `submit/*` refs still point at the same small CI proof-
receipt patch (`a1b9041f`) that diverges from the current local candidate.
Deleting those refs would discard an unabsorbed delta; pushing protected refs
before a fresh local closeout would make remote state outrun local evidence.

## What Changes

- Establish an owner-bound final reconciliation carrier for the remaining
  divergent remote submit history.
- Integrate the exact submit tip through an ordinary merge only, then execute
  local proof and governed candidate/accepted closeout before any remote push.
- Require per-ref non-force push dry-runs, distinct remote observations, and
  deletion only after every submit tip is an ancestor of accepted truth.
- Retire this carrier only after its evidence-bound local and remote lifecycle
  has completed; foreign Work Lanes remain outside its mutation authority.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=maintainer-final-dual-remote-submit-absorption; reuse=extend; change=modify; facet:lifecycle=authoring,validation,closeout,publish,retirement; facet:surface=ci,docs,openspec,evidence,claim; facet:authority=source,test,openspec,claim,evidence.

## Impact

- CI templates, generated provider projections, CI architecture regression, and
  a proof-receipt owner script from the exact submitted patch.
- This Change, its continuation claim and Chronicle, governed local closeout, and
  no-force GitLab/GitHub publication observations.

## Out Of Scope

- Force-push, rebase, reset-based ref movement, stash-based conflict bypass, release/tag work, or remote deletion before accepted ancestry proves absorption.
- Mutation, retirement, deletion, or semantic absorption claims for foreign or missing-lease `work/*` lanes.
- Any inference that a local proof or ref equality establishes hosted CI success.
