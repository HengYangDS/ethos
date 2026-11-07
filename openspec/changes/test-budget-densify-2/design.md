# Design

## Context

See [proposal.md](proposal.md). Effective lines count code lines, including bracket-only and
parametrize-case lines, and leave out docstrings, comments and blank lines (`src/ethos/measure.py`).
Ruff keeps a construct exploded while its magic trailing comma stays, even when it fits within the
100-column limit.

## Goals / Non-Goals

Goals:

- Free test headroom without weakening any test.

Non-goals:

- Removing or merging tests, or changing any assertion.
- Changing the repository's formatter configuration.

## Decisions

- **One mechanical pass, proven by the syntax tree.** The pass formats the test tree with
  `skip-magic-trailing-comma = true`, then with the repository's configuration. Each changed module
  must parse to the same `ast.dump` as before. A semantic change is then impossible, and coverage
  of product code cannot move.
- **The repository's formatter stays the owner.** The collapsed constructs carry no magic comma, so
  `ruff format --check` with the repository's configuration keeps them. Later edits keep the
  repository's usual behavior.

## Risks / Trade-offs

- Parametrize tables that fit within 100 columns now sit on one line. They read as one table
  instead of one case per line. Tables longer than the limit keep one case per line.
