## Why

Hosted CI is failing because read-only source verification is coupled to local
mutation readiness, repository executables are resolved through ambient PATH,
and runtime lock export rediscovers Python instead of selecting its bound
interpreter. These failures must close at their shared owners, not be bypassed.

## What Changes

- Separate hosted gate observation from local proof and lane/runtime admission.
- Bind hosted verification to the declared coverage floor and official OpenSpec
  validation, with exact expected HEAD and fail-closed execution receipts.
- Resolve OpenSpec through installed repository supply and bind runtime uv
  invocations to their authenticated interpreter.
- Preserve actionable failed-command diagnostics instead of empty summaries.

## Capabilities

### Modified Capabilities

- `quality`: hosted verification is exact-object observation, not mutation authority.

## Impact

Existing CI owner scripts and provider projections, runtime tool invocation,
and focused regression tests. No new lane, parser, state store, compatibility
mode, adopter changes, or reduced quality threshold. Historical lane disposal
is out of scope; the rejected preservation prototype is not revived.
