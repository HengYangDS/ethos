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
- Execute current-HEAD proof and archive this source-level convergence carrier.
- Preserve the first archive as historical evidence; foreign Work Lanes remain
  outside this continuation's mutation authority.

## Completion Boundary

This carrier ends when its ordinary merges, parity receipt, executed local proof,
and OpenSpec archive are complete.  The same session then performs the
candidate/accepted closeout and per-ref remote effects from the accepted state;
those effects are not falsely pre-certified by this archived source carrier.

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
