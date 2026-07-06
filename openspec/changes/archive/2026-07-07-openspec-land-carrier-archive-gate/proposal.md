---
subject: ethos:openspec-land-carrier-archive-gate
reuse: extend
change: modify
facet:lifecycle: land
facet:surface: openspec
facet:authority: repository-governance
---

# OpenSpec Land Carrier Archive Gate

## Why

Active OpenSpec change carriers are valid authoring context inside Work Lanes,
but they must not be promoted as active repository truth during land. Leaving a
carrier under `openspec/changes/<id>` after implementation lets stale intent pass
into candidate and defers the failure to closeout.

## What Changes

- Land-time mutation admission blocks any active OpenSpec carrier in a Work Lane.
- Completed active carriers keep the more specific completed-unarchived gap.
- Candidate and accepted-root closeout active-carrier checks remain unchanged.

## Impact

Agents must archive/fuse the OpenSpec carrier before landing. This strengthens
the existing repository truth boundary without adding a new command surface or
truth store.
