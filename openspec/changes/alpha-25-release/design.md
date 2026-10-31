# Design

## Context

See [proposal.md](proposal.md). The supply Dockerfile hashes eight inputs into the image's manifest;
`locale-independent-text` changed none of them, so the image bound for `v0.2.0-alpha.24` stays
bound. This Change is prepared in the lane that carries `locale-independent-text`, after its
archive, so one proof of the lane head covers both Changes and one landing publishes them.

## Goals / Non-Goals

**Goals:**

- One curated `0.2.0-alpha.25` entry names every user-visible change since `v0.2.0-alpha.24` and the
  known advisories in the release's shipped bytes.

**Non-Goals:**

- Changing any supply version or the supply image.

## Decisions

- **Read the advisories on the exact head.** The release build's audit of the lane head decides the
  Security notes, and the tag waits for it again.
- **Tag after the hosted runs of the landed head pass on both peers.** The release repairs Windows
  hosts, so the Windows jobs' result on the landed head is known before the tag.

## Risks / Trade-offs

- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
- [A governed Python repository fails the new Ruff rule] → Its rebind names the encoding at each
  reported site; the counts on 11-01 are in `locale-independent-text`'s proposal.
