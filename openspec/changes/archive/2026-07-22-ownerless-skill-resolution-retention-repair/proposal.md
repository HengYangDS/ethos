## Why

The accepted dbf17ff352e530e673366c9806a25c05331ddc95 range asserted
that current Ruff policy rejected direct print calls in repo-local skill
scripts. Canonical policy actually ignores T201 for
.agents/skills/**/scripts/*.py, so the recorded quality premise, accepted
specification delta, active Claim, and archived carrier do not describe
repository truth.

The same lifecycle exposed a separate product defect. A successful
preserve-retire wrote its decision, package, and receipt below the invoking
carrier worktree. Ordinary carrier retirement then removed that ignored
build tree, so the retained recovery package disappeared even though no
manifest-bound clear transition occurred. Current report and publish readiness
do not detect this loss.

## What Changes

- Forward-revert the invalid semantic delta introduced by the six-commit
  e54b81d..dbf17ff range without reset, force, or protected-ref mutation. Remove
  its false Claim, Chronicle, plan, archived carrier, duplicate specification
  scenario, and style-only script changes while preserving later accepted
  changes to shared specification and parity files.
- Route new lane-resolution decisions, preservation packages, receipts, clear
  receipts, inventory, and verification through the configured accepted
  checkout's sibling records owner:
  <accepted-checkout-parent>/<accepted-checkout-name>-records/
  recovery/lane-resolution/.
- Reserve the deterministic completion-receipt destination before package
  creation or destructive effect. Existing final receipts or concurrent
  reservations fail closed without deleting the lane; post-effect receipt
  failure retains explicit reconciliation state.
- Keep read-only compatibility for legacy
  build/artifacts/lane-resolution/ records, but block ordinary Work Lane
  retirement whenever the selected worktree still contains a retained legacy
  manifest.
- Reconcile the lost ownerless package after local closeout by rebuilding a new
  ownerless recovery lane from the still-reachable source commit and the exact
  retained tracked patch bytes, then issuing a new non-reusable native
  preserve-retire decision. The old decision ID, receipt, and bundle are not
  recreated or claimed as retained.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repository-governance`: subject=lane-resolution-retention-integrity;
  reuse=extend; change=modify; facet:lifecycle=validation,runtime,retention,
  archive; facet:surface=cli,docs,openspec,evidence,test;
  facet:authority=source,test,docs,openspec,claim,evidence

## Out Of Scope

- Changing the Ruff T201 policy, preserving the invalid skill-script carrier,
  rewriting Git history, restoring historical Codex runtime state, editing
  JSONL or SQLite by hand, reusing the old decision/receipt identifiers,
  claiming the unavailable old bundle is byte-identical, touching another Work
  Lane, GitHub mutation, or remote publication before fresh final proof.
