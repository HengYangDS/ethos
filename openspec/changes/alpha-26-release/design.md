# Design

## Context

See [proposal.md](proposal.md). This Change is prepared in the lane that carries the five product
Changes, after their archives, so one proof of the lane head covers all six Changes and one landing
publishes them. The supply image hashes eight inputs, and none of them changed since
`v0.2.0-alpha.25`, so the bound image stays bound.

## Goals / Non-Goals

**Goals:**

- One curated `0.2.0-alpha.26` entry names every user-visible change since `v0.2.0-alpha.25` and the
  known advisories in the release's shipped bytes.
- The shipped adopter CI model selects the latest stable `jdx/mise-action`.

**Non-Goals:**

- Changing a Python, npm or Mise lock, or the supply image.
- Migrating governed repositories to the new root rules; their owners repair their own roots.

## Decisions

- **Read the advisories on the exact head.** The release build's audit of the lane head decides the
  Security notes, and the tag waits for it again.
- **Pin the action by the commit its release tag names.** The model keeps commit pins; `v5.2.5`
  names `6612f0ef07ed2a736cd1e00a94a065522dd41195`, as the forge API reports for the tag.
- **Tag after the hosted runs of the landed head pass on both peers.** The release repairs hosted
  verification itself, so its result on the landed head is known before the tag.

## Risks / Trade-offs

- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
- [Four governed repositories gain a `CONTRIBUTING.md` gap on upgrade] → The gap names the file and
  its repair; the owners have the list and plan the file in their own Changes.
