# Proposal

## Why

A declaration that nothing reads back is false until it is checked. The common pipeline model's
protected job runs only on a protected ref. Several governed repositories protected one branch on
a peer, so a push of the accepted branch and of a release tag created no pipeline there, and
nothing reported it. Read in the source on 2026-11-14: `protected_refs` is a declared input of
release configuration, publication admission and the paradigm report, and no reader asks a peer
which refs it protects. `ethos publish` reports a published ref, which states the push alone.

The owner admitted two rows of the hosted leg on 2026-11-14, outside the gate's count and one at a
time: forge settings read back at publication, and one reader of hosted acceptance in the
product. The second is the reader that the `hosted-observation` draft builds.

One governed product's session offered a wider form: a contract for the resources a repository
holds on a forge, with their state read back and their drift reported.

## What Changes

- A read-only check at publication asks each peer whether it protects the refs that the
  repository declares, with the gap `peer_ref_unprotected:<peer>:<ref>`.
- Setting protection stays an act of the forge's owner.
- The wider contract for forge resources is designed with the structure rules after 0.2.0.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

Publication's admission and the forge adapters, read-only. Until it lands, forge owners protect
the accepted branch and the release tags on each peer by hand.

Owner: the release lead. Next action: take the first weekly off-gate slot that is free. Read
again: at each weekly cut, when the slot is assigned.
