## 1. Authority and rollback

- [ ] 1.1 Admit this Claim, Chronicle, plan, OpenSpec delta, scope, and owned
  Work Lane before implementation.
- [ ] 1.2 Forward-revert the invalid six-commit skill-script range and verify
  the inverse range tree against e54b81d.

## 2. Retention ownership

- [ ] 2.1 Add failing tests proving a caller Work Lane cannot own new retained
  decisions, packages, or receipts.
- [ ] 2.2 Route new resolution artifacts to the accepted-owner sibling records
  root and retain legacy inventory/clear compatibility.
- [ ] 2.3 Reject explicit decision paths outside supported roots and report
  conflicting duplicate decision records fail-closed.

## 3. Retirement and partial transitions

- [ ] 3.1 Add a failing retirement regression with an ignored legacy retained
  manifest in the selected Work Lane.
- [ ] 3.2 Block worktree/ref/lease removal while legacy retained material is
  present.
- [ ] 3.3 Add and implement honest partial-transition reporting when immutable
  receipt materialization fails after a preservation effect.

## 4. Validation and closeout

- [ ] 4.1 Run focused tests and canonical lint, then strict OpenSpec, claims,
  docs, parity, default proof, and full exact-HEAD proof.
- [ ] 4.2 Archive the completed carrier, refresh parity, prove the archived
  HEAD, land to candidate, and complete accepted-root closeout.
- [ ] 4.3 Rebuild one new ownerless recovery lane from source commit
  87911a89faeb01d97a29afce1c24e0fc5ed94f2a plus the exact patch digest,
  issue a new native preserve-retire, and verify accepted-root inventory after
  the lane is absent.
- [ ] 4.4 Synchronize authorized GitLab dev and main, verify hosted
  observation, stop the GitHub HOLD guard, and retire this owned carrier only
  after all local artifacts remain discoverable.
