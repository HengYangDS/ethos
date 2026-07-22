## 1. Authority and rollback

- [x] 1.1 Admit this Claim, Chronicle, plan, OpenSpec delta, scope, and owned
  Work Lane before implementation.
- [x] 1.2 Forward-revert the invalid six-commit skill-script semantic delta
  while preserving later accepted changes to shared files.

## 2. Retention ownership

- [x] 2.1 Add failing tests proving a caller Work Lane cannot own new retained
  decisions, packages, or receipts.
- [x] 2.2 Route new resolution artifacts to the accepted-owner sibling records
  root and retain legacy inventory/clear compatibility.
- [x] 2.3 Reject explicit decision paths outside the canonical write root and report
  conflicting duplicate decision records fail-closed.

## 3. Retirement and partial transitions

- [x] 3.1 Add a failing retirement regression with an ignored legacy retained
  manifest in the selected Work Lane.
- [x] 3.2 Block worktree/ref/lease removal while legacy retained material is
  present.
- [x] 3.3 Add and implement honest partial-transition reporting when immutable
  receipt materialization fails after a preservation effect.
- [x] 3.4 Close independent review findings for decision immutability, path
  escape, pinned self-retire ownership, ambiguous duplicate clear, durable
  manifest/receipt binding, and caller-policy redirection.

## 4. Validation and archive

- [x] 4.1 Run focused tests and canonical lint, then strict OpenSpec, claims,
  and docs validation.
- [x] 4.2 Archive the completed carrier through the official OpenSpec
  transition.

## Post-archive transition boundary

After archive, update archive-bound Claim paths, refresh parity, prove the
archived HEAD with default and full exact-HEAD proof, land to candidate, and
complete accepted-root closeout. Only then may the executor rebuild one distinct
recovery lane from source commit 87911a89faeb01d97a29afce1c24e0fc5ed94f2a
plus the exact patch digest, issue a new native preserve-retire, verify stable
inventory after the lane is absent, synchronize authorized GitLab dev and main,
observe hosted state, stop the GitHub HOLD guard, and retire this owned carrier.
