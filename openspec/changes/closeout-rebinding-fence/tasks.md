# Tasks

## 1. Fence

- [ ] 1.1 Detect pending rebindings read-only and report them from the closeout preview and
      `status`. Done when a test shows that after an interrupted rename the preview reports both
      pending gaps with the bound apply as next action, `status` names the same, and no `HEAD`
      changes.
- [ ] 1.2 Bind by compare-and-swap only in an authorized apply. Done when a test shows that an
      apply without `--authorize` or with another head binds nothing, the authorized apply binds
      both worktrees, and a worktree that moved after detection keeps its `HEAD` with the stale
      gap.
- [ ] 1.3 Probe the Git floor before any rename write. Done when a test shows that with the probe
      refused the rename apply reports `branch_role_rename_git_unsupported` and every ref and `HEAD`
      is unchanged.

## 2. Record retirement coverage

- [ ] 2.1 Test the record retirement preview's refusal and foreign-record branches. Done when tests
      cover the real runtime selection, a damaged Attestation set, an absent accepted branch, floors
      and bounds read from the accepted binding, foreign requests, receipts and artifacts, archives
      over the decode budget, and the inline and manifest-release failure branches, and the suite's
      branch coverage is at or over its 95 % floor.

## 3. Acceptance

- [ ] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
