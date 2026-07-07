---
subject: ethos:coordination-invalid-state-projection
reuse: extend
change: modify
facet:lifecycle: status
facet:surface: command-json
facet:authority: repository-governance
---

# Coordination Invalid-State Projection

## Why

Work Lane coordination already surfaces advisory signals such as foreign lanes
and missing leases. Those signals were visible but not reduced to the shared
invalid-state taxonomy inside the coordination package, leaving a small but
important measurement gap.

## What Changes

- `status.data.coordination` includes an `invalid_states` projection over its
  required and advisory coordination gaps.
- `foreign_work_lane_*` signals classify as `change_unbounded`, matching their
  lifecycle-boundary semantics.
- Workspace-status schema and schema samples require the projection.

## Impact

Coordination remains advisory unless it already has required gaps; this change
adds measurement and discoverability, not new mutation authority.
