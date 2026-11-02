# Design

## Context

See [proposal.md](proposal.md). This Change is prepared in the lane that carries `owned-literals`,
after its commits, so one proof of the archived lane head covers both Changes and one landing
publishes them. The supply image's inputs did not change since `v0.2.0-alpha.26`, so the bound
image stays bound.

## Goals / Non-Goals

**Goals:**

- One curated `0.2.0-alpha.27` entry names every user-visible change since `v0.2.0-alpha.26` and the
  known advisories in the release's shipped bytes.
- The release's adopter path is accepted on an upgrade from `v0.2.0-alpha.26`, which also exercises
  `v0.2.0-alpha.26` as the rollback target, so its missing acceptance record is covered.

**Non-Goals:**

- Changing a Python, npm or Mise lock, an action pin or the supply image.
- Deciding the owner's risk acceptance for npm 12.2.1's bundled advisories; the gate reports them
  without blocking while npm 12.2.1 is the registry latest.

## Decisions

- **Read the advisories on the exact head.** The release build's audit of the lane head decides the
  Security notes, and the tag waits for it again.
- **Tag after the hosted runs of the landed head pass on both peers.** Only GitHub runs the Windows
  and macOS hosts, so the landed head's runs are the last cross-platform evidence before the tag.

## Risks / Trade-offs

- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
- [`owned-literals` reaches adopters in the same release] → It changes no name or default: the
  declared values equal the ones it replaces, which its architecture check and the full proof cover.
