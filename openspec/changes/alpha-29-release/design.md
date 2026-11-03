# Design

## Context

See [proposal.md](proposal.md). This Change is prepared in the lane that carries ten other
Changes, after their archives, so one proof of the archived lane head covers all of them and one
landing publishes them. The supply image hashes both Python locks, the npm lock and the Mise
configuration and lock, so moving them requires an image built from them before GitLab accepts
the head.

## Goals / Non-Goals

**Goals:**

- Every supply pin is its latest stable release that the repository's constraints admit, and the
  one that is not names its blocker.
- One curated `0.2.0-alpha.29` entry names every user-visible change since `v0.2.0-alpha.28` and
  the known advisories in the release's shipped bytes.
- The release's adopter journey passes on macOS and Linux from the published prerelease.

**Non-Goals:**

- Raising `requires-python` beyond `<3.15`.
- Changing an adopter's supply; each owner moves its own.

## Decisions

- **Each owner's native resolver moves its pins.** `mise lock` and `uv lock --upgrade` select the
  releases; nothing is edited by hand except the exact pins and floors that a resolver keeps.
- **Move what is admissible now, and uv when Mise admits it.** Syft and the Python packages move
  first, so the gates that run them are known to pass before uv's age clears; uv 0.13.7 then moves
  alone in Mise and in the `uv>=` floors.
- **Build the image from the proposal.** The hosted `supply_image` workflow accepts a proposal ref,
  so the lane binds the image built from its own locks and lands once.
- **Verify the release head on every platform in parallel.** The proposal push runs every
  commit-scoped job except Windows on Arm; a manual dispatch on the same proposal ref runs
  Windows on Arm beside it, so the landed head's hosted runs cover every supported platform
  without waiting for `dev`'s run of the same commit.
- **Read the advisories on the exact head.** The release build's audit of the lane head decides the
  Security notes, and the tag waits for it again.

## Risks / Trade-offs

- [A moved tool changes a gate's findings] → The gates that run each moved tool pass on the moved
  supply before the proof.
- [Another advisory appears before the tag] → The pre-tag audit refuses the tag, and the fix lands
  in its own Change.
