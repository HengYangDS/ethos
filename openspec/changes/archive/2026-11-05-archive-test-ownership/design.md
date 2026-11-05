# Design

## Context

See [proposal.md](proposal.md). The repository paradigm limits each Python file to 500 effective
lines. Over the limit, the remedy is a split by semantic ownership, not compression.

## Goals / Non-Goals

Goals:

- Both modules under the ceiling, each with one subject.

Non-goals:

- Any change to a test's assertions or fixtures.

## Decisions

- The split follows the archive command's two concerns: whether an archive is admitted, and how it
  compensates when an admitted effect fails. Compensation tests share their own imports.
- The module docstrings name each subject.

## Risks / Trade-offs

- None. The same tests run with the same fixtures, and the collected count is unchanged.
