## 1. Admission and history preservation

- [x] 1.1 Start the owner-bound Work Lane from the current candidate head.
- [x] 1.2 Create the active OpenSpec carrier, exact scope, claim, and Chronicle.
- [x] 1.3 Re-observe all protected and submit refs immediately before merge.
- [x] 1.4 Merge the shared final submit tip with an ordinary merge and review
  conflicts.

## 2. Local proof and closeout

- [x] 2.1 Refresh changed-path parity and run the required local gates.
- [x] 2.2 Execute a HEAD-bound proof and archive the carrier without false
  completion.

## Post-Commit Lifecycle Boundary

This archived carrier records only its completed local admission, ordinary
merge, parity, and HEAD-bound archive-transition proof. The following
downstream transitions remain mandatory, are governed by
`dual-remote-final-closeout-continuation-20260718`, and are not asserted by
this archive:

- governed candidate land, candidate-external control verification, and
  accepted-root closeout that reconcile local `dev`, `main`, and `candidate/dev`;
- ordinary per-ref non-force push dry-runs followed only by accepted protected
  updates to GitLab and GitHub;
- fresh remote/provider and hosted-CI observations kept as distinct evidence;
  and
- per-ref deletion dry-runs, deletion only after accepted ancestry, and
  owner-bound Work Lane retirement.

Archive admission therefore closes this historical carrier without replacing,
implying, or pre-authorizing any downstream mutation.
