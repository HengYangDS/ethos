# Design

## Context

See [proposal.md](proposal.md). alpha.29 applied the 24-hour release age by hand: it reverted the
Python locks to `dev` and moved only the packages whose floors had to move. A peer measured a native
form on 11-04 against three repositories' scratch copies. `uv lock --upgrade --exclude-newer`
admits only releases published before the cutoff. A plain `uv lock` then removes the
`exclude-newer` option that the first command writes into the lock, and moves nothing.

## Goals / Non-Goals

Goals:

- Ship the lane's three product Changes as `0.2.0-alpha.30`.
- Apply the release age through uv's own resolver.

Non-goals:

- Moving packages younger than 24 hours. These are filelock 4.2.8, platformdirs 4.14.4,
  python-discovery 1.9.4 and virtualenv 21.15.5, all published on 11-04; they move after 11-05
  15:46 CST.
- Moving Mise. It stays at 2026.10.25 until upstream fixes jdx/mise#15363.

## Decisions

- Take the cutoff from the time of the move and record it in the task. It is the only input that
  makes the move reproducible.
- If no package moves, the supply image is not rebuilt, and its binding stays as it is.

## Risks / Trade-offs

- A move rebuilds the supply image, which adds one hosted build before the proposal runs.
