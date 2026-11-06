# Design

## Context

See [proposal.md](proposal.md). The source budget counts bracket-only and per-element lines, so a
construct that a magic trailing comma keeps exploded costs one line per element. The formatter
keeps `skip-magic-trailing-comma = false`; removing a comma lets it decide the layout again.

## Goals / Non-Goals

Goals:

- `python_tests` at most 94,740 effective lines, so the open lanes land with margin.

Non-goals:

- Any change to a test's code, to the formatter configuration or to a ceiling.

## Decisions

- **Let the formatter decide.** Each module is formatted once with magic trailing commas ignored
  and then checked with the repository's configuration, which keeps that output. Only modules that
  no other open lane changes are touched, so no lane must resolve a conflict.

## Risks / Trade-offs

- A list that was one element per line for reading is now one line; each still fits within 100
  columns.
