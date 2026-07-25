---
subject: ethos:budget-contract-v2-snapshot-replay-shadow-successor-preservation-clear-20260725
role: plan
state: active
relations:
  source_decision: lane-decision:f912ef18-c897-481b-b3b1-d8e48de61e2e
  source_claim: budget-contract-v2-snapshot-replay-shadow-successor-absorption-20260725
  change: openspec/changes/archive/2026-07-25-budget-contract-v2-snapshot-replay-shadow-successor-preservation-clear
---

# Snapshot-Replay Shadow Successor Preservation Clear — 2026-07-25

Status: active local-only authority carrier.

Purpose: clear one semantically superseded recovery package through the native,
manifest-bound `lane_resolution/clear-preservation` transition while retaining
the original decision, completion receipt, and a new clear receipt.

See also: [Snapshot-Replay Shadow Successor Absorption Design](budget-contract-v2-snapshot-replay-shadow-successor-absorption-design-20260725.md),
[Snapshot-Replay Shadow Successor Absorption Implementation](budget-contract-v2-snapshot-replay-shadow-successor-absorption-implementation-plan-20260725.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

## Exact deletion boundary

The only candidate package is the canonical sibling recovery-records package
for decision `lane-decision:f912ef18-c897-481b-b3b1-d8e48de61e2e`. Native
`preserve-retire` created it for
`work/20260724-budget-contract-v2-snapshot-replay-shadow-successor` at
`fb9f8348559c0e881bfe9692988f59c3bf9dd85a`. Its exact manifest SHA-256 is
`b4477425826dbd214ea4cf3796bf288fe8b8cf6b769b70d77c79a049e2ae40b4`.

The package contains a complete Git bundle with SHA-256
`755171796a4158b2f6083d1c36bba032f3d0927dc1401feb15e39376379e4407`
and a native tracked patch with SHA-256
`a28501235292ff13f76aea6e385c436206e7c6586361b534f30d434af0127e69`.
Applying that patch to the bundled source HEAD reconstructs the pre-effect
full-index patch SHA-256
`63a72e73f2d9719724f1ce04c39ae451be70789578ed971fac017d546b05dd94`.
The index patch is empty, and no untracked archive exists.

The immutable completion receipt is
`1286e83871b9fdc7574ad1adb3b0f9ea53849e4493d8f7822a5609fe43e38369.json`;
its file SHA-256 is
`8743ece68be31bcdb9a0693c65ab30fbff1c7667c0b52dcd9b3aae98fecbcf77`.

## No-unique-behavior basis

Accepted HEAD `8555afde76dff73572d278789315a5bde8ed9399` includes the
target-specific absorption Chronicle, archived OpenSpec delta, canonical
repository-governance requirement, and the exact or stronger source-budget
behavior mapped from all ten dirty paths. Its executed 21-gate proof completed
with evidence digest
`fc31d85bf6206ecff46c816276b8faf8dc5e6849114c029a446207827c39f700`
and no required gap.

The retained bytes therefore reconstruct the superseded implementation but add
no behavior absent from accepted truth. Whole-file replay remains rejected
because it would remove the accepted v2 policy loader and weaken current public
measurement boundaries.

## Required transition

After this carrier reaches accepted local closeout, invoke only native clear for
this decision id and manifest. The command must re-read inventory and manifest
bytes, retain the original decision and completion receipt, remove only that
package, and emit a clear receipt. Any manifest drift, conflicting copy, missing
receipt, or newly discovered behavior blocks the effect.

## Boundaries

This carrier authorizes no other package clear, raw filesystem removal, receipt
deletion, source reconstruction, branch or lease mutation, Work Lane takeover,
remote mutation, hosted claim, or batch retention sweep. The carrier itself is
retired only after the clear receipt and final inventory are checked.
