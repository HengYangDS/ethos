## Why

An active change can pass strict OpenSpec validation yet fail only at the final
`openspec archive` mutation because its delta cannot be applied to the current
accepted spec. The recent `ADDED Requirement` collision is one instance; the
official archive can also reject missing modified or removed requirements,
rename collisions, dropped scenarios, structural faults, and an existing
archive target. A late archive failure leaves a completed Work Lane unable to
close even though the failure was determinable without mutating repository
truth.

## What Changes

- Run the official OpenSpec archive command against an isolated temporary copy
  of the OpenSpec workspace for every active change reviewed in lifecycle mode.
- Project official archive diagnostics into structured lifecycle evidence and
  required gaps before proof, land, or accepted-root closeout.
- Preserve the official archive as the sole delta-application authority: ETHOS
  neither reimplements its parser nor rewrites `ADDED`, `MODIFIED`, `REMOVED`,
  or `RENAMED` operations automatically.

## Capabilities

### Modified Capabilities

- `adapters`: subject=openspec-archive-preflight; reuse=extend; change=modify;
  facet:lifecycle=plan,prove,land; facet:surface=openspec;
  facet:evidence=official-cli,temporary-projection; facet:authority=change,claim

## Out Of Scope

- Patching, wrapping, or replacing the official OpenSpec archive implementation.
- Mutating a source OpenSpec workspace during preflight.
- Automatically reclassifying a change delta or completing its tasks.
