---
subject: ethos:artifact-topology-detached-residue-preservation-clear-20260725
role: plan
state: active
relations:
  source_decision: lane-decision:56a318b4-18e5-4a73-9051-80202eb99576
  source_claim: artifact-topology-detached-residue-absorption-20260724
  change: openspec/changes/archive/2026-07-25-artifact-topology-detached-residue-preservation-clear
---

# Artifact-Topology Detached Residue Preservation Clear — 2026-07-25

Status: active local-only authority carrier.

Purpose: clear one now-superseded recovery package through the native,
manifest-bound `lane_resolution/clear-preservation` transition while retaining
the original decision, completion receipt, and a new clear receipt.

See also: [Detached Residue Absorption Design](artifact-topology-detached-residue-absorption-design-20260724.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

## Exact deletion boundary

The only candidate package is the canonical sibling recovery-records package
for decision `lane-decision:56a318b4-18e5-4a73-9051-80202eb99576`. It was
created by native `preserve-retire` for
`work/artifact-topology-hotpath-20260714@70defe82f306708badf1cfabe0c3f8fa917287fa`.
Its exact manifest SHA-256 is
`d4f4f64ad401a4f0131bc5eaa9d40cb267d28c6f41e26a9b94afadb23140a2ed`.

The package contains a complete Git bundle and a tracked patch whose SHA-256 is
`6a84df8a7b28d703f82f1bcac0ee61e8534874438e25c7376c38d8c81f5a404a`.
That patch is byte-identical to the pre-effect source capture. The index patch
is empty, and no untracked archive exists. The bundle contains only the exact
historical source ref and complete history needed for reconstruction.

## No-unique-behavior basis

The accepted absorption carrier maps every historical hunk family to current
behavior or an explicit rejection. Accepted HEAD
`69bd7fa5df82b789ae1324e87c6a393da5f4293f` passed the focused topology/CEL
suite and a 21-gate executed proof with evidence digest
`7812b6669476eb9ec4c554cf819e2139271fd9db0d1ad99d95598cf307e34173`.
The retained bytes therefore reconstruct the rejected historical
implementation but add no behavior absent from accepted truth.

## Required transition

After this carrier reaches accepted local closeout, invoke only native clear for
this decision id and manifest. The command must re-read the exact package,
retain the original decision and completion receipt, remove only that package,
and emit a clear receipt. Any manifest drift, conflicting copy, missing receipt,
or newly discovered behavior blocks the effect.

## Boundaries

This carrier authorizes no other package clear, raw filesystem removal, receipt
deletion, branch or lease mutation, Work Lane takeover, remote mutation, hosted
claim, or batch retention sweep. The carrier itself is retired only after the
clear receipt and final inventory are checked.
