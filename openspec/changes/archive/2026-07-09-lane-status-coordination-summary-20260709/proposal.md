# Lane Status Coordination Summary

## Why

`ethos status --json` and `ethos orient --json` expose Work Lane coordination
small signals at first glance, but `ethos lane status --json` kept its summary
mostly count-only. During multi-agent work, that forces humans and agents to
open the full payload before seeing missing leases, dirty foreign lanes,
advisory counts, or the coordination next action.

## What Changes

- Lift existing `data.coordination` fields into `ethos lane status --json`
  summary.
- Keep the fields derived and read-only; they do not change Work Lane authority
  or turn advisory signals into required gaps.
- Document the command contract and add focused regression coverage.

## Capabilities

- `repository-governance`: subject=lane-status-coordination-summary; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,docs,openspec,evidence,test; facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- No new command, truth store, lane lifecycle state, or cleanup authority.
- No automatic retirement, absorption, or mutation of foreign Work Lanes.
- No change to the blocking versus advisory classification produced by
  workspace status.
