# Proposal

## Why

A native archive can produce a valid canonical spec with blocking INFO guidance. ETHOS then blocks status and proof, but its corrective prewrite admits only invalid archived specs. The original Change is no longer active, so the owner cannot repair the exact file without bypassing governance.

## What Changes

- Admit an exact canonical-spec repair when current official INFO findings and a verified archive effect identify the same authored output, including multiple findings in one spec.
- Keep ordinary proof blocked until fresh validation clears the findings; reject unrelated paths and unverified archive or validation evidence.
- Give blocked status an actionable corrective prewrite rather than a dead-end observation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: extend canonical guidance repair to an attested archive output.

## Impact

The existing OpenSpec current-resolution and repair-scope owners, plus public status/prewrite regressions. No warning waiver, second lifecycle, or adopter-specific path rule.
