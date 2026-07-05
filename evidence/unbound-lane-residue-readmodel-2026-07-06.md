---
subject: ethos:unbound-lane-residue-readmodel
role: evidence
state: complete
---

# Unbound Lane Residue Read Model Evidence — 2026-07-06

## Claim

ETHOS status now exposes unbound Work Lane refs as inspectable coordination
residue objects rather than count-only advisory signals.

## Evidence

- Focused tests passed for lane status, CLI status, workspace-status schema, and
  coordination package edges.
- `ethos quality schemas --json` reported clean.
- Live lane status emitted `work/dissolve-cache-table` with
  `relation_to_accepted=diverged_from_accepted` and an inspection next action.

## Boundary

This evidence supports read-model visibility only. It does not assert that the
old branch can be deleted, merged, or superseded without a separate decision.
