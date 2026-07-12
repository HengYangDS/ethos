## Why

`evidence/claims/` currently admits two persisted claim shapes: the trust-bearing
canonical envelope and a historical top-level change-claim shape. The latter
keeps a second parser, a second report projection, and tests for a format that
no longer represents the product's claim protocol. It increases maintenance
surface while allowing older records to bypass the envelope's explicit
freshness and trust-carrier vocabulary.

## What Changes

- Migrate every tracked top-level change claim to the canonical `[claim]` /
  `[evidence]` envelope, preserving its subject, lifecycle meaning, evidence
  reference, OpenSpec carrier, and promotion targets.
- Remove the runtime branch that parses and projects top-level change claims.
- Make a non-envelope claim file a deterministic required gap instead of a
  compatibility path.
- Preserve claim-report JSON semantics for canonical records and add migration
  parity tests for all converted records.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=claim-envelope; reuse=extend;
  change=modify; facet:lifecycle=validation; facet:surface=evidence,read-model;
  facet:authority=source,test,openspec,evidence.

## Impact

Affected surfaces are `evidence/claims/`, the claim report reducer, focused
claim-governance tests, the repository-governance specification, and the
bounded claim/evidence/OpenSpec carrier for this migration. No public command,
external service, or new dependency is introduced.

## Out Of Scope

- Reformatting or reinterpreting already-canonical claim envelopes beyond facts
  required to eliminate the top-level alternate format.
- Changing historical evidence into a current-head or hosted-enforcement claim.
- Adding a new claim service, workflow runtime, or compatibility adapter.
