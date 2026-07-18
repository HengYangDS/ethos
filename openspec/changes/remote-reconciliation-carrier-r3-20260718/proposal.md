## Why

On 2026-07-18, local accepted and candidate refs agree at one commit, while the
four protected refs at the configured GitLab and GitHub forges point to four
distinct commits. Fast-forward-only updates cannot reconcile those histories;
force updates would discard reachable history.

## What Changes

- Establish an evidence-bound maintenance carrier for this exact remote
  reconciliation episode.
- Require the reconciliation head to retain every fresh observed protected tip
  through ordinary merge ancestry before a protected-ref update is considered.
- Keep local proof, local closeout, remote ref observation, and hosted-provider
  observation separate evidence classes.

## Capabilities

- `repository-governance`: subject=maintainer-remote-reconciliation; reuse=extend; change=modify; facet:lifecycle=authoring,validation,closeout,publish; facet:surface=docs,openspec,evidence; facet:authority=source,openspec,claim,evidence

## Out Of Scope

- No force update, rebase, reset-based ref movement, stash-based conflict
  bypass, release, version change, or tag.
- No claim that local proof establishes remote equality or hosted-provider
  success.
- No mutation of foreign Work Lanes or their artifacts.
