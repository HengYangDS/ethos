## Why

The archived first carrier retained an ordinary merge of the original submit
tip, but `candidate/dev` and the shared GitLab/GitHub submit tip advanced while
the archive transition was completed.  The first carrier therefore cannot
truthfully certify candidate land, accepted-root closeout, protected updates,
or submit deletion.

## What Changes

- Bind the existing remote-reconciliation claim to this active continuation.
- Refresh from the current candidate, re-observe submit and protected refs, and
  retain the current divergent submit tip through an ordinary merge.
- Execute current-HEAD proof, candidate/accepted closeout, per-ref no-force
  push dry-runs and updates, then delete only submit refs proved absorbed.
- Preserve the first archive as historical evidence; foreign Work Lanes remain
  outside this continuation's mutation authority.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=maintainer-final-dual-remote-closeout; reuse=extend; change=modify; facet:lifecycle=validation,closeout,publish,retirement; facet:surface=openspec,evidence,claim,ci; facet:authority=source,test,openspec,claim,evidence.

## Out Of Scope

- Force-push, rebase, reset-based ref movement, stash-based conflict bypass,
  tags/releases, or deletion before accepted ancestry and a per-ref dry-run.
- Mutation, retirement, deletion, or semantic absorption claims for foreign or
  missing-lease `work/*` lanes.
- Any inference that local proof establishes remote or hosted CI success.
