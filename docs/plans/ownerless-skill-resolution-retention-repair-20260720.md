---
subject: ethos:ownerless-skill-resolution-retention-repair-20260720
role: plan
state: active
relations:
  carrier: openspec/changes/ownerless-skill-resolution-retention-repair-20260720
  supersedes: ownerless-skill-scripts-semantic-closeout-20260720
---

# Ownerless Skill Resolution Retention Repair Implementation Plan

Status: active closeout carrier; Tasks 1 through 3 and the reservation hardening
commit are complete. Task 4 owns authoring validation, archive, proof, land, and
accepted closeout.

Purpose: remove one invalid carrier without rewriting history, retain
non-rebuildable lane-resolution recovery outside disposable worktrees, and
reconcile one lost ownerless patch through a new bounded transition.

See also: [Command Plane](../reference/command-plane.md),
[Local State](../architecture/local-state.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

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

**Files:** this plan, Claim, Chronicle, active OpenSpec carrier, and the full
e54b81d..dbf17ff invalid semantic range.

- [x] Commit the admitted carrier and bind its Claim to the owned lane.
- [x] Enumerate the full six-commit range and apply a no-commit inverse that
  removes its invalid semantic delta while preserving later accepted changes
  to shared specification and parity files.
- [x] Commit the signed forward revert; never reset or force a protected ref.

## Task 2: Red tests for stable ownership and legacy blocking

**Tests:** tests/unit/lanes/test_lane_resolution_artifacts.py,
tests/unit/lanes/test_lane_resolution.py, and
tests/unit/lanes/test_lanes_retire.py.

- [x] Add a multi-worktree test that invokes preserve-retire from a carrier and
  observes records below the sibling records owner.
- [x] Retire the carrier in the fixture and prove accepted-root inventory and
  verification still succeed.
- [x] Add legacy retained-manifest and duplicate-decision conflict tests.
- [x] Add receipt-write failure coverage that expects partial-transition output.
- [x] Run the focused tests and observe the new assertions fail for the intended
  missing behavior.

## Task 3: Minimal implementation

**Files:** resolution `_shared.py`, `_observation.py`, `_effects.py`,
`record_store.py`, `lane.py`, `receipts.py`, CLI resolution, ordinary retirement
shared core, and the Ruff ignored-rule ratchet.

- [x] Implement accepted control-root and sibling records-root resolution.
- [x] Route new decision/package/receipt/clear writes to the stable owner while
  retaining bounded legacy reads for inventory, verify, and clear.
- [x] Merge canonical and legacy read sources with duplicate conflict blocking.
- [x] Block ordinary retirement over a legacy retained manifest.
- [x] Convert receipt-write failure after effect into explicit partial state.
- [x] Run focused tests and canonical Ruff until green; do not refactor unrelated
  lifecycle code.
- [x] Close independent review findings for decision immutability, path escape,
  self-retire receipt ownership, ambiguous duplicate clear, durable
  manifest/receipt binding, and caller-policy redirection.
- [x] Reserve the deterministic receipt destination with a hidden non-JSON
  `O_CREAT|O_EXCL` sidecar before package creation or destructive effect; block
  existing final or reservation paths with
  `lane_resolution_receipt_path_exists`.
- [x] Release reservations after pre-effect failure or successful receipt write,
  retain them after post-effect write failure, and preserve the final writer's
  independent no-clobber check.
- [x] Split observation, effects, and record storage below the 500-effective-line
  limit and shrink Ruff ratchets without adding exemptions.

## Task 4: Specification and carrier archive

**Files:** command-plane/local-state docs, canonical repository-governance spec,
OpenSpec tasks/archive, Claim/Chronicle, and parity evidence.

- [ ] Update docs, the lane's canonical specification, delta, Claim, and
  Chronicle from the green implementation. The canonical edit becomes accepted
  truth only after accepted-root closeout.
- [ ] Validate focused gates, strict OpenSpec, claims, and docs.
- [ ] Archive the completed carrier through the official OpenSpec transition.
- [ ] Update archive-bound carrier paths and refresh generic parity in this lane.
- [ ] Run default and full exact-HEAD proof on the archived HEAD.
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
