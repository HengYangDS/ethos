# Design

## Context

See the [proposal](proposal.md). The suite-wide pytest timeout (600 seconds) already ends a hung
test; a per-test marker exists to end one sooner, and its literal counted setup time as well.

## Goals / Non-Goals

Goals:

- A loaded host does not fail a test that would pass.
- A literal per-test timeout below the tool deadline cannot be added again.

Non-Goals:

- Timeouts that a test passes to the code under test to provoke a timeout on purpose.

## Decisions

1. Each marker becomes `@pytest.mark.timeout(seconds("tool"))`.
2. The guard parses the test tree and refuses `pytest.mark.timeout(<number>)` when the number is
   below `seconds("tool")`; a marker that names a deadline is allowed.

## Risks / Trade-offs

- A real hang in one of these tests now ends after the tool deadline instead of two to thirty
  seconds; the suite still ends it long before its own timeout.
