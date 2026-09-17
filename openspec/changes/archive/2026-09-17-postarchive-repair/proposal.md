## Why

Official archive can leave a canonical specification that strict validation
rejects. Current repair admission requires the active Change that archive has
removed, so valid exact repairs cannot reach proof or accepted closeout.

## What Changes

- Extend the existing validator-named repair owner to consume verified archived
  intent when no active Change remains, without treating evidence as permission.
- Preserve current coordination, exact requested paths, structured validation
  observations and postimage checks across prewrite and host admission.
- Verify successful repair and rejection of unrelated, ambiguous or stale
  inputs through existing public surfaces, then remove superseded assumptions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: canonical specification repair after official archive.

## Impact

Current resolution, official OpenSpec repair scope, existing admission tests
and the canonical terminal plan. The scope excludes new carriers, persisted
repair state, archive replay, adopter source changes, generic publication
fallback repair and a second plan or lifecycle. Archived content remains
historical evidence; current authority and exact effect checks still apply.
