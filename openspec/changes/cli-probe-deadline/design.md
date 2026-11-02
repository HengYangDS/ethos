# Design

## Context

See [proposal.md](proposal.md). The module checks the hosted projections by running the tools they
name: the ETHOS CLI, the toolchain bootstrap, `bash`, `cue`, the projection renderer and pytest.
Each start costs seconds on an idle host and more on a loaded one.

## Goals / Non-Goals

**Goals:**

- These checks fail when a projected command is wrong, not when its host is slow.

**Non-Goals:**

- The other literal timeouts in the suite. Many bound deliberately small children in the process
  adapter's own timeout tests, so each needs its own reading.

## Decisions

- **Use `seconds("tool")`.** The paradigm already declares the bound of one tool run, and a test
  invocation without a bound repository reads its default.

## Risks / Trade-offs

- [A hung tool now holds its test for up to 60 seconds] → The pytest timeout of 600 seconds still
  bounds the test, and a hang still fails it.
