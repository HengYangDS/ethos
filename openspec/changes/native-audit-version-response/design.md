# Design

## Context

The existing quality spec owns unfixed-upstream reporting. Its audit adapter captures a bounded
registry observation and passes it to the shared acceptance algebra. The current npm command
returns a JSON string; older single-element array responses remain valid inputs.

## Goals / Non-Goals

**Goals:** accept native version responses at their existing reader and retain strict missing-input
and fixable-finding decisions.

**Non-Goals:** change acceptance policy, reuse old registry answers, add a wrapper, approve installation
risk or alter supply and release ownership.

## Decisions

1. Normalize a single-element array within the existing reader, then accept a nonempty string.
   A separate parser or new integration layer would add no semantic responsibility.
2. Remove the test transport's response rewriting. Existing audit journeys must exercise the
   actual scalar response as well as the retained array shape.
3. Keep the original observation deadline, raw native evidence and acceptance algebra. Parsing a
   version does not itself grant permission; the existing owner still evaluates each finding.

## Risks / Trade-offs

- Unexpected response shapes remain unobserved and therefore cannot authorize an audit decision.
- Focused tests prove the reader contract, not the installed supply or complete release workflow.
