## Why

work/20260724-budget-contract-v2-snapshot-replay-shadow-successor is now a
dirty linked Work Lane with no current lease, Claim, process, opener, or current
owner assignment. Raw cleanup would lose recoverable bytes. Replaying its old
Task 4 patch would regress current accepted config and byte-measurement
boundaries.

## What Changes

- Bind the exact source head, merge base, dirty paths, timestamps, and patch
  digests.
- Record which useful semantics current accepted source owns exactly or more
  strictly and which whole-file replay is explicitly rejected.
- Permit one later native preserve-retire transition only after this carrier is
  proven, archived, landed, and locally closed out.
- Keep recovery-package clear separate and exact-manifest-bound.
- Keep every valid-owner foreign lane observe-only.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=expired-dirty-successor-semantic-absorption;
  reuse=extend; change=modify; facet:lifecycle=authoring,validation,retirement;
  facet:surface=openspec,claim,chronicle,docs;
  facet:authority=git,evidence,test,native-command.

## Out Of Scope

Historical product replay, valid-owner takeover, foreign-lane write or
retirement, broad cleanup, raw ref deletion, remote publication, hosted claims,
or package clearing before a later accepted exact-manifest decision.
