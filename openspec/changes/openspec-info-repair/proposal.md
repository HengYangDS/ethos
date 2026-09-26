# Proposal

## Why

ETHOS currently blocks proof on a valid canonical OpenSpec specification's INFO finding, but its corrective prewrite path recognizes only invalid specifications. An adopter cannot edit the exact files needed to clear the finding under its Work Lane. Re-reading status does not resolve that cycle.

## What Changes

- Admit corrective prewrite for an existing canonical spec only when current official validation names a matching, valid spec INFO finding and the selected Change, actor, and Lease remain valid.
- Keep ordinary status, proof, commit, and publication strict until the finding is removed. Do not grant unrelated paths or a new authoring scope.
- Give status an actionable repair continuation instead of repeating an observation that cannot change the result.
- Reuse one official validation-envelope parser across gap reporting and repair selection; add adversarial and public-entry regressions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: make strict canonical OpenSpec findings correctable without weakening proof or unrelated write admission.

## Impact

The existing OpenSpec validation observation, repair-scope derivation, current-resolution continuation, and their tests. No new lifecycle, persistent authority, warning suppression, or adopter-specific exception.
