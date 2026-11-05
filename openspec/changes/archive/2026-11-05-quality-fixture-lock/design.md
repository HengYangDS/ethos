# Design

## Context

See [proposal.md](proposal.md). The fixture declares only a `dev` group: pytest, pytest-cov,
pytest-reportlog and ruff. Its lock resolves 11 packages, and all of them also appear in the
repository lock.

## Goals / Non-Goals

Goals:

- The fixture lock follows every repository lock move.
- A drift fails as a named difference, not as an evidence refusal several layers down.

Non-goals:

- Generating the fixture lock from the repository lock. It stays a native `uv` lock of its own
  project.

## Decisions

- **Move with uv.** The fixture lock is written natively, with the hashes from uv's own resolution:
  `uv lock --project tests/fixtures/quality-sample --upgrade-package coverage==7.17.1`.
- **State the rule in an architecture test.** The test reads both locks with `tomllib` and compares
  the versions of the packages they share. A lock move that forgets the fixture fails this test in
  seconds, ahead of the behavior gate.

## Risks / Trade-offs

- None found. The fixture's dependency floors (`>=`) stay as they are, and only its lock pins move.
