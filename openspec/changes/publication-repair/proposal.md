## Why

Live publication at accepted `4f6998ff` recognizes repaired-history descendants
in commit-range admission but rejects them again as non-fast-forward at the
accepted-ref boundary. The existing obligations must compose consistently.

## What Changes

- Consume the verified repair replacement as the accepted-forward baseline,
  while retaining candidate equality, current proof and accepted effect checks.
- Exercise public pre-push and two-peer publication after a real historical
  repair and ordinary signed descendant, including missing evidence failures.
- Record the late-boundary counterexample in the existing terminal plan and
  preserve the failed preview as evidence instead of retrying it unchanged.

- Preserve nested immutable evidence when serializing native hook rejection,
  retaining the decision without a traceback or eager policy startup.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: preserve candidate, proof and exact-CAS obligations
  when publishing a verified repair followed by ordinary accepted commits.

## Impact

The existing publication admission owner and native publication tests. No new
parser, persistent cache, dependency, contributor restriction, credential change
or adopter write. Active-Change selection and proposal retirement remain
separate bounded fixes in the canonical terminal plan.
