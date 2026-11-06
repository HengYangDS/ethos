# Design

## Context

See [proposal.md](proposal.md). The terminal ceiling is the source budget's own decision. The
policy raises it by one 5,000-line step only when removing accidental complexity cannot bring the
measure under it, so this Change removes duplication first.

## Goals / Non-Goals

Goals:

- `python_tests` is at most 94,880 effective lines, which leaves room for the next Change.

Non-goals:

- Any product change, any change to a ceiling, or any assertion removed.

## Decisions

- **One helper per repeated call.** A call repeated with the same arguments inside one module
  becomes a module-local helper, so the module states the call once and each test states only what
  differs.
- **One assertion per observed shape.** A run of assertions on fields of one result becomes one
  tuple comparison, which fails with the same information.

## Risks / Trade-offs

- A shared helper hides the call from a reader of one test; each helper is named after what it does
  and stays in the module that uses it.
