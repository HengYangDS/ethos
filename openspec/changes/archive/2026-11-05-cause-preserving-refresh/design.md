# Design

## Context

See [proposal.md](proposal.md). The native merge refresh reports conflicts and requires their
paths to be admitted, resolved and staged before `--mode continue`.

## Goals / Non-Goals

Goals:

- Keep every line of both sides.

Non-goals:

- Any edit beyond joining the two sides.

## Decisions

- Each side's text is kept unchanged. No line is shared by both sides, which the resolver checks.
- The changelog stays valid under `changelog_errors`.

## Risks / Trade-offs

- None beyond the merge.
