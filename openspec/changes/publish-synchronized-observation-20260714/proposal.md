# Publish Synchronized Tracking Observation

## Problem

`ethos publish --probe-remote --json` exposed a synchronized remote-tracking
ref in a nested field but still labeled the publication observation as
`deferred`. This conflated two distinct facts: the command does not push, while
the already-observed remote ref can nevertheless equal the local HEAD.

## Change

Project a `synchronized` remote publication observation only when the local
remote-tracking ref is synchronized. Preserve `remote_push = "not_performed"`,
keep mutation admission deferred, and make the next action explicitly say that
no push was performed.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=publish-tracking-observation; reuse=extend; change=modify; facet:lifecycle=readiness,publication; facet:surface=cli,domain,test,openspec,claim,evidence; facet:authority=source,test,openspec,claim,evidence

## Out of scope

No remote push, hosted-CI assertion, credential use, network adapter, or change
to lane/closeout authority is introduced.
