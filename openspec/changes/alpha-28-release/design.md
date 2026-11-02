# Design

## Context

See [proposal.md](proposal.md). This Change is prepared in the lane that carries
`absorbed-proposal-retirement`, `landing-proof-authority`, `cli-probe-deadline` and
`effect-marker-deadline`, after their archives, so one proof of the archived lane head covers all of
them and one landing publishes them. The supply image hashes eight inputs, among them both Python
locks, the npm lock and the Mise configuration and lock, so moving them requires an image built from
them before GitLab accepts the head.

## Goals / Non-Goals

**Goals:**

- Every supply pin is its latest stable release that the repository's constraints admit, and the
  one that is not names its blocker.
- One curated `0.2.0-alpha.28` entry names every user-visible change since `v0.2.0-alpha.27` and the
  known advisories in the release's shipped bytes.
- The release's adopter path is accepted on an upgrade from `v0.2.0-alpha.27`.

**Non-Goals:**

- Raising `requires-python` beyond `<3.15` while a locked dependency has no CPython 3.15 wheel.
- Changing an adopter's supply; each owner moves its own.

## Decisions

- **Each owner's native resolver moves its pins.** `mise lock`, `uv lock --upgrade` and `npm update`
  select the releases; nothing is edited by hand except the exact pins that a resolver keeps.
- **Allow npm's tarball fetch for the update only.** npm 12 refuses `npm update` because the locked
  `npm` package resolves to its registry tarball; the update runs with `--allow-remote=all`, and the
  resulting lock is accepted only when every resolved URL is the public registry.
- **Build the image from the proposal.** The hosted `supply_image` workflow accepts a proposal ref, so
  the lane binds the image built from its own locks and lands once.
- **Read the advisories on the exact head.** The release build's audit of the lane head decides the
  Security notes, and the tag waits for it again.
- **Tag after the hosted runs of the landed head pass on both peers.**

## Risks / Trade-offs

- [A moved tool changes a gate's findings] → The gates that run each moved tool pass on the moved
  supply before the proof.
- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
- [Adopters rebind again soon after `v0.2.0-alpha.27`] → An adopter that has not proved its
  `v0.2.0-alpha.27` binding yet can bind `v0.2.0-alpha.28` instead, in the same Change.
