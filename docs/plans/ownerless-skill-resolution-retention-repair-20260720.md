---
subject: ethos:ownerless-skill-resolution-retention-repair-20260720
role: plan
state: active
relations:
  carrier: openspec/changes/ownerless-skill-resolution-retention-repair-20260720
  supersedes: ownerless-skill-scripts-semantic-closeout-20260720
---

# Ownerless Skill Resolution Retention Repair Implementation Plan

> **For agentic workers:** execute task-by-task with TDD, exact-HEAD evidence,
> and reviewer checkpoints. Do not mutate accepted, candidate, or foreign lanes.

**Goal:** Remove the false skill-script semantic carrier, make retained
lane-resolution recovery survive carrier retirement, and reconstruct one honest
new recovery package for the lost ownerless patch.

**Architecture:** New resolution writes use the configured accepted checkout's
sibling <repo>-records/recovery/lane-resolution owner. Legacy per-worktree
records remain readable, but a retained legacy manifest blocks ordinary
retirement. The deleted historical receipt is never recreated; a new
Chronicle-bound recovery lane produces a new package and receipt.

**Tech Stack:** Python 3.12+, Git worktrees, ETHOS command plane, OpenSpec,
pytest, Ruff, JSON/TOML evidence.

## Global Constraints

- All ETHOS commands run through tools/ci/scripts/run-ethos-lane.sh.
- ETHOS_ACTOR=agent:openai:thread:root.
- No force, reset of protected refs, --no-verify, GitHub write, manual
  JSONL/SQLite mutation, shared app-server kill, or foreign-lane mutation.
- Tracked writes require current lane status and exact-path lane prewrite.
- The old decision, receipt, and unavailable bundle are historical loss; new
  records use new identifiers and make no byte-identity claim for the bundle.
- Remote publication follows fresh default and full exact-HEAD proof, local
  accepted closeout, and stable artifact inventory.

## Task 1: Admit the successor and invert the invalid range

**Files:** this plan, Claim, Chronicle, active OpenSpec carrier, and the exact
20-path e54b81d..dbf17ff range.

- [ ] Commit the admitted carrier and bind its Claim to the owned lane.
- [ ] Run a no-commit inverse only after enumerating the full six-commit range;
  verify the resulting changes exactly match the range paths and restore their
  tree content to e54b81d.
- [ ] Commit the signed forward revert; never reset or force a protected ref.

## Task 2: Red tests for stable ownership and legacy blocking

**Tests:** tests/unit/lanes/test_lane_resolution_artifacts.py,
tests/unit/lanes/test_lane_resolution.py, and
tests/unit/lanes/test_lanes_retire.py.

- [ ] Add a multi-worktree test that invokes preserve-retire from a carrier and
  observes records below the sibling records owner.
- [ ] Retire the carrier in the fixture and prove accepted-root inventory and
  verification still succeed.
- [ ] Add legacy retained-manifest and duplicate-decision conflict tests.
- [ ] Add receipt-write failure coverage that expects partial-transition output.
- [ ] Run the focused tests and observe the new assertions fail for the intended
  missing behavior.

## Task 3: Minimal implementation

**Files:** resolution _shared.py, lane.py, receipts.py, CLI resolution, and
ordinary retirement shared core.

- [ ] Implement accepted control-root and sibling records-root resolution.
- [ ] Route decision/package/receipt/inventory/verify/clear consistently.
- [ ] Merge canonical and legacy read sources with duplicate conflict blocking.
- [ ] Block ordinary retirement over a legacy retained manifest.
- [ ] Convert receipt-write failure after effect into explicit partial state.
- [ ] Run focused tests and canonical Ruff until green; do not refactor unrelated
  lifecycle code.

## Task 4: Specification, proof, and local closeout

**Files:** command-plane/local-state docs, canonical repository-governance spec,
OpenSpec tasks/archive, Claim/Chronicle, and parity evidence.

- [ ] Update docs and accepted specification from the proven behavior.
- [ ] Validate strict OpenSpec and claims, then archive the carrier officially.
- [ ] Refresh generic parity in the owned lane.
- [ ] Run focused gates, default exact-HEAD proof, and full exact-HEAD proof.
- [ ] Land to candidate and run audited accepted-root closeout.

## Task 5: Lost-package reconciliation and publication

**Local effects:** one new temporary ownerless recovery lane and canonical
records-root artifacts.

- [ ] Verify the 9,673-byte patch SHA-256 and source commit before creating any
  recovery lane.
- [ ] Create a new distinct recovery branch at the source commit, apply the
  exact patch, and confirm git diff --binary HEAD -- has the same digest.
- [ ] Use a new decision and receipt with this Chronicle's
  lane_resolution/preserve-retire authority.
- [ ] Verify package/receipt inventory from accepted root after the recovery lane
  is absent.
- [ ] Re-run report/publish readiness, atomically synchronize authorized GitLab
  dev and main, observe hosted state, stop the GitHub HOLD guard, and retire
  this owned carrier.
