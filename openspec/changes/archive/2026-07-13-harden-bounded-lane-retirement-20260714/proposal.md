## Why

A targeted `ethos lane retire landed --branch <owned-lane>` currently evaluates
every registered Work Lane before narrowing to the requested branch. A stale
foreign worktree path can therefore raise `FileNotFoundError` and prevent the
owner from retiring its otherwise proven, merged lane. The failure is a local
control-plane robustness defect: it neither produces a bounded verdict nor
preserves the requested lane's lifecycle path.

## What Changes

- Restrict branch-targeted landed-retirement inspection to the selected Work
  Lane before any lane-local Git status call.
- Make lane cleanliness inspection fail closed for unavailable paths, returning
  a deterministic blocked retirement state rather than raising an exception.
- Add regression coverage proving a missing foreign worktree cannot block a
  matching owner's targeted retirement, while unavailable selected lanes remain
  non-retireable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=bounded-landed-lane-retirement; reuse=extend;
  change=modify; facet:lifecycle=mutation,retirement; facet:surface=cli,openspec,
  evidence,test; facet:authority=source,test,openspec,claim,evidence

## Out of Scope

- No remote probe, remote publication, or hosted CI claim.
- No foreign Work Lane cleanup, Git worktree prune, lease repair, or branch deletion.
- No relaxation that treats an unavailable selected worktree as clean.

## Impact

Affected surfaces are ETHOS lane-retirement adapters, their unit coverage, and
one OpenSpec archive. No remote probe, remote publication, adopter runtime, or
foreign lane cleanup is performed.
