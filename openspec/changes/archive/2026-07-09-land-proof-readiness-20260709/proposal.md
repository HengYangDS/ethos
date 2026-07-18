# Land Proof Readiness

## Why

A Work Lane can appear `ready_to_land` in dry-run land output while a subsequent
HEAD-bound executed proof fails. That hides a small but decisive disorder signal:
landability is being described before proof evidence is bound to the exact HEAD.

## What Changes

- `ethos land --json` for Work Lanes reports `proof_not_proven` until a valid
  executed proof record exists for the current HEAD.
- The land payload exposes a `proof_readiness` read model with the HEAD, state,
  required gaps, and exact proof command.
- Existing apply-time proof enforcement remains unchanged.

## Capabilities

- `repository-governance`: subject=land-proof-readiness; reuse=extend; change=modify; facet:lifecycle=validation; facet:surface=cli,openspec,test; facet:authority=source,test,openspec

## Out Of Scope

This does not create a second proof store. It reads the existing local
HEAD-keyed executed-proof record and makes the missing/fresh state visible in
land readiness.

- No new proof store, command plane, or hosted CI claim.
- No change to accepted-root closeout semantics in this lane.
- No relaxation of apply-time proof enforcement.
