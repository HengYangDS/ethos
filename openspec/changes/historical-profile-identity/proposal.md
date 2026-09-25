## Why

A completed author-identity repair and a later accepted closeout become
impossible to publish after ETHOS tightens its current repository-profile
schema: historical effect revalidation parses former commits with today's full
profile model. Those commits still identify the same repository, but an
obsolete non-identity field blocks `ethos publish --peer` before remote
admission.

## What Changes

- Revalidate historical repair coordinates and recorded Git effects from each
  exact committed profile's stable `profile_id`, without requiring an old
  profile to satisfy the current operational schema.
- Keep the current checkout's strict profile validation, the original repair
  coordinates, policy and payload hashes, effect Attestations, replacement
  history, proof and remote compare-and-swap unchanged.
- Cover a retired profile field in both repair and accepted-closeout replay,
  plus absent, malformed and mismatched historical identities.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: immutable repair and accepted-effect provenance
  remains verifiable across profile-schema evolution without accepting a
  different repository identity.

## Impact

The existing profile observation adapter, Git-effect Attestation validator,
signature-repair provenance reader, native tests and repository-governance
contract. No adopter-specific exception, compatibility profile, second
authority store, remote write path or new dependency is added.
