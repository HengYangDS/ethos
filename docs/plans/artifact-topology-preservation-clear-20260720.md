---
subject: ethos:artifact-topology-preservation-clear-20260720
role: plan
state: active
relations:
  source_decision: lane-decision:48f82dc4-cc1a-4c25-8a48-f02ccce2c5fb
  source_receipt: build/artifacts/lane-resolution/receipts/15f0d02bd440439e43a5f80322abad675383d8682e3a5993702f709754393c5b.json
---

# Artifact-Topology Preservation Clear — 2026-07-20

Status: active, local-only authority carrier.

Purpose: remove one now-proven-superseded recovery package through the native,
manifest-bound `lane_resolution/clear-preservation` transition, while retaining
the immutable decision and completion receipt.

See also: [Artifact-Topology Hotpath Absorption](artifact-topology-hotpath-absorption-20260720.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

## Exact deletion boundary

The only candidate package is
`build/artifacts/lane-resolution/lane-decision:48f82dc4-cc1a-4c25-8a48-f02ccce2c5fb`.
It was created by the native `preserve-retire` decision for the retired source
`work/artifact-topology-hotpath-repair-20260714` at
`194b2ec91891631f178ef7c71d73da35e77c6b13`. Its exact manifest SHA-256 is
`fe52fec8149efb0e2edb2cf4f22fdc31b510b90848ac971f14348bb8ad41b757`; its
sole tracked patch SHA-256 is
`408937fa6e4993c208189856427fec823fc3d4ecf52a0e24d87d03d775ac26d6`.

The package contains a Git bundle and that historic parity projection. The
current accepted generic parity evidence has since been regenerated on
`f55fed5ef32e0fc73df71f270df6519a9d121232`; the retained patch changes only
stale head, semantic-digest, command-path, and timeout metadata. It supplies
no product behavior absent from the accepted topology/CEL proof and closeout.

## Required transition

After this carrier is accepted locally, invoke only:

```text
ethos lane resolution clear
  --decision-id lane-decision:48f82dc4-cc1a-4c25-8a48-f02ccce2c5fb
  --expect-manifest-sha256 fe52fec8149efb0e2edb2cf4f22fdc31b510b90848ac971f14348bb8ad41b757
  --chronicle-ref evidence/chronicle/artifact-topology-preservation-clear-20260720/2026-07-20.md
  --break-glass --confirm-irreversible --apply
```

The native command must re-read the package and exact manifest before removal,
leave the original decision and immutable receipt intact, and create its own
clear receipt. Any manifest drift, absent acceptance, or new unique behavior
blocks deletion.

## Boundaries

This carrier authorizes no other package clear, source rewrite, raw filesystem
removal, branch/lease deletion, Work Lane takeover, remote mutation, or hosted
CI claim. It is retired after its own accepted local closeout and the one clear
receipt is verified.
