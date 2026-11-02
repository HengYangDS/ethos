# Design

## Context

See [proposal.md](proposal.md). `kill_after_marker` polls for a marker file that the child writes
right after its real effect, and stops early when the child exits. Its deadline only bounds a child
that neither exits nor reaches its marker.

## Goals / Non-Goals

**Goals:**

- A child that is slow because its host is loaded still reaches its marker before the test gives
  up.

**Non-Goals:**

- Other literal waits in the suite, such as the process adapter's own timeout tests, which bound
  deliberately small children.

## Decisions

- **Use `seconds("tool")` and drop the parameter.** The child is one run of an ETHOS command, which
  the paradigm bounds by the tool deadline; no caller needs a different bound.

## Risks / Trade-offs

- [A hung child now holds its test for up to 60 seconds] → The pytest timeout of 600 seconds still
  bounds the test, and a child that exits without its marker still fails at once.
