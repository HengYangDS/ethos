# Design

## Context

The archived `gate-fail-closed` Change owns the behaviour and its `quality` requirements. The
release notes are curated in `CHANGELOG.md` and are read by adopters' owners when they move to a
release.

## Goals / Non-Goals

Goals: the next release's notes name the contained gate failure as adopters will see it.

Non-Goals: a changelog coverage check, which stays a deferred item of the gates program.

## Decisions

1. One `### Changed` bullet, in the register of its neighbours. It states what an adopter sees:
   the gaps, the verdict classes, and that every other gate keeps its evidence.

## Risks / Trade-offs

- None beyond wording; the archived Change remains the authority for the behaviour.
