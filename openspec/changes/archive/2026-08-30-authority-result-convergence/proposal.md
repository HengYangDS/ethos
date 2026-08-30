## Why

Status, plan, prewrite, and hook surfaces currently re-interpret the same
repository facts independently. This produces contradictory gaps, prose-only
remediation, and Continuation decisions inferred from command text instead of
typed authority facts.

## What Changes

- Replace command-local authority and current-Change interpretation with one
  typed current-resolution owner.
- Make the public result algebra carry an explicit user-decision fact and derive
  Continuation without parsing `next_action` text or gap-name suffixes.
- Project one first exact gap and one executable next action consistently across
  status, plan, prewrite, and hooks.
- Delete superseded local action tables, fallback prose, and duplicate authority
  interpretation after their unique semantics move to the common owner.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: Public result and authority projections converge on one
  typed resolver and one closed Continuation algebra.

## Impact

The change affects the result contract, current repository authority
resolution, status/plan/prewrite/hook projections, their public schema, and
focused regression tests. It adds no persistent state, carrier, registry,
compatibility path, or second error taxonomy.
