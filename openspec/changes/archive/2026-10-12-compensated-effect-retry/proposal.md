## Why

A Work Lane start can create its ref, fail in a later projection step and then
delete the ref through an attested compensation. On 2026-10-12 an adopter hit
this when hook activation could not write `.git/config` inside an agent
sandbox. Every identical retry then selects the earlier creation Attestation
for the same plan, checks it against current refs and blocks with
`git_effect_attestation_content_mismatch`. Starting the same branch from a
later candidate succeeds, but Change provenance then sees two lane births and
refuses implicit selection.

## What Changes

- Treat an applied effect as closed when a later, historically valid
  Attestation records its exact inverse under the same assertions. Both
  Attestations remain unchanged members of the set.
- Exclude closed effects from exact-plan recognition, so an identical fresh
  plan is re-admitted against current refs and applied again.
- Exclude a compensated Work Lane start from the lane-birth boundary that Change
  provenance reads.
- Derive the executor's reverse transaction and the Work Lane start
  compensation from one inverse definition.
- Add real-Git regressions for the identical retry, unattested or forged
  reversal, and a restart after compensation.

Out of scope: whether Work Lane start should keep an attested ref and complete
its projections forward instead of compensating; reuse of a lane name after a
non-inverse effect such as retirement; any change to the adopter repository,
its Attestation set or its selected runtime.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-transaction`: an attested exact inverse closes its forward effect
  for exact-plan recognition and lane-birth provenance.

## Impact

The Git effect contract, its Attestation reader, the executor's compensation,
Work Lane start compensation, OpenSpec lane-birth selection and their native
tests. No new authority store, Attestation predicate, data migration or
adopter-specific path is introduced; existing Attestations are read, never
rewritten.
