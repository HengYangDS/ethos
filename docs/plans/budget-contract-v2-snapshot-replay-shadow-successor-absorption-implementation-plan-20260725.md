---
subject: ethos:budget-contract-v2-snapshot-replay-shadow-successor-absorption-implementation-20260725
role: plan
state: active
relations:
  implements: budget-contract-v2-snapshot-replay-shadow-successor-absorption
  companion: docs/plans/budget-contract-v2-snapshot-replay-shadow-successor-absorption-design-20260725.md
---

# Snapshot-Replay Shadow Successor Absorption Implementation Plan

Status: active local-only execution plan.

Purpose: execute semantic absorption, accepted closeout, exact source
preservation-retirement, manifest-bound package clear, and owned-lane
housekeeping.

See also: [Design](budget-contract-v2-snapshot-replay-shadow-successor-absorption-design-20260725.md),
[Mutation Rules](../../rules/mutation.md), and
[Evidence Rules](../../rules/evidence.md).

> For agentic workers: execute inline through the ETHOS lifecycle. Do not
> delegate or mutate any foreign valid-owner lane.

**Goal:** Semantically absorb and safely retire the exact dirty ownerless
work/20260724-budget-contract-v2-snapshot-replay-shadow-successor without
replaying superseded implementation or discarding recoverable bytes.

**Architecture:** A current-candidate authority carrier records exact source
facts and the accepted semantic replacements. Native preserve-retire protects
the source payload before removal. A later accepted exact-manifest carrier
separately clears only the resulting recovery package.

**Tech Stack:** Git worktrees, ETHOS lane lifecycle, OpenSpec, Claim and
Chronicle evidence, Python focused tests, and repository-family governance.

## Global Constraints

- Current date and all new tracked dates are 2026-07-25.
- Only the exact ownerless source branch may be affected.
- Valid-owner terminal and source-admission lanes remain observe-only.
- Accepted and candidate roots mutate only through audited lifecycle commands.
- No force push, raw ref deletion, broad prune, or foreign-lane mutation.
- Preservation, semantic absorption, package clearing, and carrier retirement
  are independently proved transitions.

---

### Task 1: Freeze the exact source observation

**Files:**
- Runtime evidence: build/evidence/snapshot-replay-shadow-successor-absorption/

- [x] Capture source HEAD, candidate HEAD, merge base, status-v2, dirty paths,
      file hashes, timestamps, binary patch, index patch, process occupancy,
      openers, and worktree registration.
- [x] Confirm source HEAD fb9f8348559c0e881bfe9692988f59c3bf9dd85a,
      ten unstaged tracked paths, no staged patch, no process or opener, and
      missing lease plus missing Claim after exact lease expiry.
- [x] Bind tracked patch SHA-256
      63a72e73f2d9719724f1ce04c39ae451be70789578ed971fac017d546b05dd94
      and status-v2 SHA-256
      f9a72e99b6648933b554a7a553f1184705c7cd39cc52d0e93f9ef33fe864191b.

### Task 2: Promote the semantic judgment

**Files:**
- Modify: docs/plans/README.md
- Create: docs/plans/budget-contract-v2-snapshot-replay-shadow-successor-absorption-design-20260725.md
- Create: docs/plans/budget-contract-v2-snapshot-replay-shadow-successor-absorption-implementation-plan-20260725.md
- Create: evidence/claims/budget-contract-v2-snapshot-replay-shadow-successor-absorption-20260725.toml
- Create: evidence/chronicle/budget-contract-v2-snapshot-replay-shadow-successor-absorption-20260725/2026-07-25.md
- Create: openspec/changes/budget-contract-v2-snapshot-replay-shadow-successor-absorption/

- [x] Record four alternatives and select current semantic absorption plus
      native preserve-retire and later exact-manifest clear.
- [x] Map every committed and dirty hunk family to exact or stronger current
      accepted behavior or an explicit rejection.
- [x] Validate strict OpenSpec, Claim digest, docs registry, provenance, and
      focused source-budget behavior.
- [x] Commit the authority carrier with a verified signature and bind the Claim.

### Task 3: Archive and prove the carrier

- [x] Complete only tasks backed by fresh evidence.
- [x] Run generic shadow parity and commit the refreshed evidence.
- [x] Officially archive the OpenSpec change and update the Claim carrier.
- [x] Run exact-HEAD executed proof and report with no required gap.
- [ ] Refresh immediately before land and rerun proof if the carrier HEAD changes.

### Task 4: Land and close out accepted state

- [ ] Land the exact proven carrier to candidate/dev.
- [ ] Run accepted-root closeout as a separate audited transition.
- [ ] Verify accepted, candidate, and main refs are clean and locally aligned.
- [ ] Report local publish readiness without remote push.

### Task 5: Preserve-retire the ownerless source

- [ ] Re-observe the exact source and confirm no valid owner, lease, Claim,
      process occupancy, source change, or accepted-basis drift appeared.
- [ ] Record a native preserve-retire decision bound to the accepted Chronicle.
- [ ] Dry-run apply, then apply with exact decision path and irreversible
      confirmation.
- [ ] Verify manifest, receipt, patch digest, source branch absence, worktree
      absence, and accepted-root cleanliness.

### Task 6: Clear only the exact retained package

- [ ] Compare the package manifest and payload to the accepted semantic map.
- [ ] Create, prove, archive, land, and close out a separate exact-manifest clear
      carrier.
- [ ] Dry-run then apply native clear for only the exact decision and manifest.
- [ ] Verify the package is absent while the decision, completion receipt, and
      clear receipt remain valid.

### Task 7: Retire owned carriers and housekeep

- [ ] Run worktree-closeout-check for each owned carrier with its exact branch,
      path, owner task, and expected HEAD.
- [ ] Retire only exactly absorbed owned carriers through native landed
      retirement.
- [ ] Run lane status, resolution inventory, repo-family audit, Git fsck,
      worktree prune dry-run, and bounded housekeeping.
- [ ] Leave valid-owner lanes and all unrelated records untouched.
