# Report Coordination Advisory

## Why

`ethos status` and `ethos orient` already expose foreign Work Lane coordination
signals, but `ethos report` could still show `advisory_gap_count=0` while linked
Work Lane residue, missing leases, or other non-blocking coordination signals
were present. That made the scorecard too easy to read as "all quiet" during
multi-agent closeout.

## What Changes

- Extend the report advisory read model to include existing workspace-status
  Work Lane coordination advisory gaps.
- Keep those signals non-blocking: required gaps remain reserved for transition
  failures.
- Add bounded read-only next actions so humans and agents inspect `orient` and
  `lane status` instead of mutating foreign lanes.

## Capabilities

- `repository-governance`: subject=report-coordination-advisory; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,openspec,evidence,test; facet:authority=source,test,openspec,claim,evidence

## Out Of Scope

- No new truth store, command plane, lane lifecycle state, or blocking gate.
- No automatic retirement of foreign, dirty, unleased, or same-claim Work Lanes.
- No change to Work Lane ownership, handoff, or break-glass authorization.
