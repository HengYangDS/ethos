# Cross-Host Handoff Fixture Compression

## Why

`tests/unit/cli/lane/test_cross_host_handoff.py` repeats the same governed
handoff-export command construction across clean, blocked, preserved, and
import preparation cases. This duplicates command binding without creating
independent behavior.

## What Changes

- Use one typed local test helper for the invariant handoff-export command.
- Keep each test's distinct context, disposition, outcome, and assertion
  explicit.
- Delete only superseded CLI test setup; do not alter product handoff semantics.

## Out Of Scope

- Production lifecycle behavior, CLI contracts, schemas, dependencies, quality
  thresholds, and foreign Work Lanes.

## Capabilities

- `quality`: subject=cross-host-handoff-fixture-compression; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=test,openspec;
  facet:authority=source,test,openspec
