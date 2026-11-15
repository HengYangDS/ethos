# Proposal

## Why

Package acceptance checks an adoption's planned files in two stages. The brownfield stage gets
the build under test from the acceptance effect and compares an ordered list. The shared
conformance of the CLI, SDK and MCP surfaces runs as a script inside the installed runtime. Since
`release-trust-repairs` it requires the exact set, and it reads whether the build is a release
through the product's own reader in its own process.

A review of that repair named what the second stage still cannot see:

- If the product classifies a build wrongly, the expectation is wrong in the same way and the
  check passes.
- If the surface that answered is another build than the script's own, the check judges one
  build by the other. Every result already names the build that answered.
- A set accepts a planned file listed twice or in another order, which the brownfield stage
  refuses.

## What Changes

Candidates; none is decided.

- The acceptance effect passes the build under test to the conformance stage, as the brownfield
  stage receives it.
- The stage refuses a result whose answering build is not the build under test.
- The stage compares the ordered list.
- Each change runs first on a release leg of the hosted run, so the design states how the lane
  tries it before a tag depends on it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

`tools/ci/delivery/acceptance/` and its tests. No product behavior changes.

Owner: the release lead. Next action: measure the patch and how a lane can run the stage on a
release build. Read again: at the cut of 0.2.0-beta.13.
