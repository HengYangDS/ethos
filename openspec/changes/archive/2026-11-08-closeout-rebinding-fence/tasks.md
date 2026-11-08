# Tasks

## 1. Fence

- [x] 1.1 Detect pending rebindings read-only and report them from the closeout preview and
      `status`. Done when a test shows that after an interrupted rename the preview reports both
      pending gaps with the bound apply as next action, `status` names the same, and no `HEAD`
      changes. At 10:34:36 the interrupted-binding, partial-binding and unreadable-table tests
      failed against the healing preview; at 10:38:35 the 21 legacy role tests passed: after an
      interrupted rename the preview reported both pending gaps with the bound apply as next action,
      `status` named the same apply, and no `HEAD` changed.
- [x] 1.2 Bind by compare-and-swap only in an authorized apply. Done when a test shows that an apply
      without `--authorize` or with another head binds nothing, the authorized apply binds both
      worktrees, and a worktree that moved after detection keeps its `HEAD` with the stale gap. At
      10:38:35 an apply without `--authorize` bound nothing, the authorized apply bound the accepted
      and candidate worktrees to `dev` and `candidate/dev`, and a worktree switched after detection
      kept its `HEAD` with `branch_role_worktree_binding_stale`; Git 2.56.0 admitted the
      compare-and-swap against a deleted legacy target in `--no-deref` mode.
- [x] 1.3 Probe the Git floor before any rename write. Done when a test shows that with the probe
      refused the rename apply reports `branch_role_rename_git_unsupported` and every ref and `HEAD`
      is unchanged. At 10:38:35, with the probe refused, the rename apply reported
      `branch_role_rename_git_unsupported` and the legacy ref and the candidate's `HEAD` were
      unchanged.

## 2. Record retirement coverage

- [x] 2.1 Test the record retirement preview's refusal and foreign-record branches. Done when tests
      cover the real runtime selection, a damaged Attestation set, an absent accepted branch, floors
      and bounds read from the accepted binding, foreign requests, receipts and artifacts, archives
      over the decode budget, and the inline and manifest-release failure branches, and the new
      modules measure at least 95 % branch coverage under them; the suite's floor stays the full
      proof's gate. At 10:29:50 the 45 retention, manifest and CLI retirement tests passed with the
      new refusal and foreign-record cases, and the new modules measured 98 % branch coverage under
      them, against 90 % before.

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. The precheck's 361 impacted test files passed at 11:45:19, 6,515 tests with 4 skipped,
      its static findings only spec lines copied verbatim from the current requirement; readiness
      passed its 28 gates at `b2014d9d1` at 11:48:39.
