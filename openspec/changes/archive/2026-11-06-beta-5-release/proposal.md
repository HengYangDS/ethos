# Proposal

## Why

Since 20:13 on 2026-11-06 the host has run mise 2026.11.2. Under it, 0.2.0-beta.4 reports npm tools
that have aube lock sidecars as missing, so the behavior gates of wib, aigw-cli and
architecture-publisher block with `mise_supply_incomplete`. `mise-lock-sidecars`, `mise-lock-module`
and `mise-lock-coverage` landed the fix. On their landed head `c08415158`, wib's 19 host checks and
aigw-cli's 11 passed under mise 2026.11.2 before release.

beta.5 is the non-breaking fix release: adopters move to it without changing their kits. It also
carries the other Changes landed since beta.4:

- `supply-move-1106` and `supply-image-currency`;
- `proof-readiness`, `proof-readiness-full-plan` and `readiness-layout-fix`;
- `private-address-class`.

The breaking result schema and the publication declaration's retired fields ship together in
beta.6, so adopters take one breaking move.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-beta.5`.
- The `0.2.0-beta.5` entry is curated from the landed Changes. It names:
  - the upgrade paths that its journey qualifies: 0.2.0-beta.4, 0.2.0-beta.2 and 0.2.0-alpha.29;
  - the journeys that this beta does not qualify;
  - the known open defects, none in a blocking class.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A release entry changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`, `VERSION` and `distributions/npm/package.json`.
