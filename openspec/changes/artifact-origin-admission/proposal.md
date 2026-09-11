## Why

Current admission infers generation from filename suffixes, rejecting ordinary
authored configuration while missing declared generated outputs. Patch admission
also loses deletions when collecting postimages, hiding surviving consumers.

## What Changes

- **BREAKING**: replace suffix-based generation assertions with native producer
  and lifecycle ownership facts; retain location constraints independently.
- Resolve existing architecture and CI projection declarations through their
  native owners, without a second generated-file registry.
- Carry exact deletion effects through patch admission and reject affected
  surviving native consumers while allowing coherent source retirement.
- Report observed ownership, existence, proposed effect and a useful next action;
  retain unknown coverage instead of claiming unsupported semantics complete.
- Repair the directly blocking quality-policy measurement boundary: one Python
  ELOC interpretation for both consumers, strict declared ceilings, and explicit
  invalid versus unavailable observations instead of coercion or fallback counts.

## Capabilities

### Modified Capabilities

- `repository-governance`: origin-aware artifact admission and deletion closure.
- `contracts`: shared fail-closed Python measurement semantics.
- `quality`: declared file-size limits and actionable observation failures.

## Impact

Existing artifact policy, native projection adapters, patch and prewrite owners,
their public regressions and the canonical terminal plan. Routing remains the
repository-governance and quality-gate owners. No adopter edits, compatibility
carrier, second lifecycle, new dependency or new Work Lane. Full program-effect
analysis and unrelated historical cleanup are not part of this bounded Change.
