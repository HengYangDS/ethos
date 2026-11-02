# Design

## Context

See [proposal.md](proposal.md). The supply image hashes the Mise configuration, the CI projection
policy and both Python locks, so the moves need an image built from them before GitLab accepts the
head. `0.2.0-alpha.28` is tagged from the previous accepted head, so this Change lands after that
tag and rides in the next release.

## Goals / Non-Goals

**Goals:**

- Every supply pin is its latest stable release that the repository's constraints admit, and the
  one that is not names its blocker.
- A Mise move changes only the Mise floor, the bootstrap version and its digests.

**Non-Goals:**

- Raising `requires-python` beyond `<3.15` while a locked dependency has no CPython 3.15 wheel.
- Changing an adopter's supply; each owner moves its own.

## Decisions

- **Each owner's native resolver moves its pins.** `uv lock --upgrade` selects the Python releases;
  the Mise digests are copied from the release's own `SHASUMS256.txt`, not computed from a local
  download.
- **The test reads the floor.** The bootstrap-version fault replaces the floor that the Mise
  configuration declares, instead of a copy of it.
- **Build the image from the proposal**, as `0.2.0-alpha.28` did, and land once.

## Risks / Trade-offs

- [The bound digests do not match an executable that CI downloads] → The hosted runs of the proposal
  stage and verify the official executable on every host before landing.
- [A moved package changes behavior] → The patch moves within one minor version; the full proof and
  both peers' hosted runs cover the head before landing.
