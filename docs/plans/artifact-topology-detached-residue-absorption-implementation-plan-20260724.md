---
subject: ethos:artifact-topology-detached-residue-absorption-implementation-20260724
role: plan
state: active
relations:
  implements: artifact-topology-detached-residue-absorption
  companion: docs/plans/artifact-topology-detached-residue-absorption-design-20260724.md
---

# Artifact-Topology Detached Residue Absorption Implementation Plan

Status: active local-only execution plan.

Purpose: execute the authority carrier, accepted closeout, exact source
preservation-retirement, and separately authorized package decision.

See also: [Design](artifact-topology-detached-residue-absorption-design-20260724.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

> **For agentic workers:** execute inline through the ETHOS lifecycle; do not
> delegate or mutate any foreign valid-owner lane.

**Goal:** Semantically absorb and safely retire the exact dirty ownerless
`work/artifact-topology-hotpath-20260714` residue without replaying superseded
implementation or discarding recoverable bytes.

**Architecture:** A current-base authority carrier records the source and
semantic judgment.  The accepted carrier authorizes one later native
preserve-retire effect; package clearing remains a separate manifest-bound
transition.

**Tech Stack:** Git worktrees, ETHOS lane lifecycle, OpenSpec, Claim/Chronicle,
Python topology tests, repository-family governance.

## Global Constraints

- Current date and all new tracked dates are 2026-07-24.
- Only the exact ownerless source branch may be affected.
- Accepted and candidate roots remain observe-only outside audited closeout.
- No force push, raw ref deletion, broad prune, or foreign-lane mutation.
- Preservation is not called semantic absorption; both must be proved
  independently.

---

### Task 1: Freeze the source observation

**Files:**
- Temporary evidence: `build/evidence/artifact-topology-detached-residue/`

- [x] Capture worktree registration, detached reflog, status-v2, dirty patch,
  file hashes, process occupancy, session ownership, and accepted comparisons.
- [x] Confirm exact HEAD
  `70defe82f306708badf1cfabe0c3f8fa917287fa` and patch SHA-256
  `6a84df8a7b28d703f82f1bcac0ee61e8534874438e25c7376c38d8c81f5a404a`.
- [x] Reconstruct `work/artifact-topology-hotpath-20260714` at that HEAD and
  attach it to the existing worktree without changing working bytes.
- [x] Re-observe the lane as dirty, linked, missing-lease, missing-Claim, and an
  accepted ancestor.

### Task 2: Promote the semantic judgment

**Files:**
- Create: `docs/plans/artifact-topology-detached-residue-absorption-design-20260724.md`
- Create: `docs/plans/artifact-topology-detached-residue-absorption-implementation-plan-20260724.md`
- Create: `evidence/claims/artifact-topology-detached-residue-absorption-20260724.toml`
- Create: `evidence/chronicle/artifact-topology-detached-residue-absorption-20260724/2026-07-24.md`
- Create: `openspec/changes/artifact-topology-detached-residue-absorption/`

- [x] Record three alternatives and select current semantic judgment plus native
  preserve-retire.
- [x] Map every dirty hunk family to absorbed current behavior or an explicit
  rejection.
- [x] Bind one target-specific Chronicle and Claim; do not mint reusable cleanup
  authority.
- [x] Validate strict OpenSpec, Claim digest, docs registry, provenance, and
  focused topology/CEL tests.
- [x] Commit the authority carrier with a verified signature.

### Task 3: Archive and prove the carrier

**Files:**
- Modify: the active OpenSpec carrier and Claim paths produced by official archive.

- [x] Complete only checkboxes backed by fresh evidence.
- [x] Run generic shadow parity in the admitted Work Lane and commit the result.
- [x] Officially archive the change.
- [ ] Run exact-HEAD executed proof and report with no required gap.

### Task 4: Land and accepted closeout

- [ ] Refresh immediately before land; rerun proof if HEAD changes.
- [ ] Land the exact proven HEAD to `candidate/dev`.
- [ ] From the accepted root, run audited closeout as a separate transition.
- [ ] Verify accepted, candidate, and release refs are clean and locally aligned
  for this carrier; do not push.

### Task 5: Native source preservation-retirement

- [ ] Re-observe the exact source lane and confirm no valid owner, lease, Claim,
  process occupancy, or source drift appeared.
- [ ] Record a native decision selecting
  `lane_resolution/preserve-retire` and binding the accepted Chronicle.
- [ ] Dry-run apply, then apply with exact expected head and irreversible
  confirmation.
- [ ] Verify preservation manifest, receipt, patch digest, branch absence,
  worktree absence, and accepted-root cleanliness.

### Task 6: Manifest-bound package decision and housekeeping

- [ ] Compare the retained package against accepted semantic carriers and the
  pre-effect staging digest.
- [ ] If no unique behavior remains, author and accept a separate exact-manifest
  `lane_resolution/clear-preservation` carrier before clearing the package.
- [ ] Retire this authority carrier only after its source transition and any
  authorized package transition are complete.
- [ ] Run lane status, repository-family audit, Git fsck, worktree prune dry-run,
  and final housekeeping.
