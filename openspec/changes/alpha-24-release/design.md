# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight inputs into the image's manifest;
`adopter-reported-repairs` changed none of them, so the image bound for `v0.2.0-alpha.23` stays
bound. This Change is prepared in the lane that carries `adopter-reported-repairs`, after its
archive, so one proof of the lane head covers both Changes and one landing publishes them.

## Goals / Non-Goals

**Goals:**

- One curated `0.2.0-alpha.24` entry names every user-visible change since `v0.2.0-alpha.23` and the
  known advisories in the release's shipped bytes.

**Non-Goals:**

- Changing any supply version or the supply image.

## Decisions

- **Read the advisories on the exact head.** The release build's audit of the landed head decides
  the Security notes, and the tag waits for it again.
- **Tag after the hosted runs of the landed head pass on both peers.** GitLab's Windows ARM64 jobs
  are the ones this release repairs, so their result on the landed head is known before the tag.

## Risks / Trade-offs

- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
- [An adopter needs the fix before its own rebind] → Each rebind is one selector and its proof; a
  repository may move from any earlier alpha straight to `0.2.0-alpha.24`.
