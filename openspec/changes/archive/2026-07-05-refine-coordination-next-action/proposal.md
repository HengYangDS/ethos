## Why

Work Lane coordination currently reports non-blocking residue such as an
unbound `work/*` ref with a generic next action about overlapping or unknown
scope. That overstates the invalid state and makes advisory cleanup look like a
candidate-integration blocker.

## What Changes

- Refine `status.data.coordination.next_action` so required, overlap, lease,
  foreign-lane, unbound-ref, and clean states receive distinct guidance.
- Keep the existing gap taxonomy and JSON shape; only the read-model guidance is
  made more precise.
- Add regression coverage for unbound Work Lane refs and coordination package
  next-action selection.

## Capabilities

- `ethos-repository`: subject=work-lane-coordination-readmodel; reuse=extend;
  change=modify; facet:lifecycle=runtime,validation; facet:surface=cli,test,openspec;
  facet:authority=source,test,openspec

## Out Of Scope

- No new Work Lane ontology.
- No new blocking gate for advisory-only coordination residue.
- No remote publication or hosted merge behavior.
