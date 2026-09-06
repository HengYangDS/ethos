## 1. Contract And RED

- [x] 1.1 Strictly validate the three modified capability deltas and confirm the
  design contains no unresolved authority, range, trust, or migration decision.
- [ ] 1.2 Add failing tests for index-bound `commit-msg` admission, including a
  malformed staged policy, a changed staged policy, and an invalid raw Git
  commit subject.
- [ ] 1.3 Add failing tests for introduced-range admission covering fast-forward,
  non-fast-forward, new proposal, absent or non-ancestor baseline, SHA-1,
  SHA-256, annotated-tag peeling, deletion, multiple updates, malformed or absent
  tip policy, invalid subject, missing/wrong-format signature, and old-history
  exclusion.
- [ ] 1.4 Add failing command, hook activation, status, and dual-provider
  projection tests proving all transports invoke the same public owner.

## 2. Unique Owner And Deletion

- [ ] 2.1 Create the semantic commit adapter package, move lifecycle creation
  and signing into its creation owner, and delete `git_signing.py` without a
  facade.
- [ ] 2.2 Implement one tip-policy, endpoint-peeling, introduced-range, and
  commit-validation owner; retain optional local trust verification for
  lifecycle effects.
- [ ] 2.3 Make configured author/committer identity consume the shared revision
  sequence and delete its range walker and duplicate ancestry helper.
- [ ] 2.4 Install and execute `commit-msg`, expose the named-coordinate
  `ethos hook commit-range` JSON command, and compose the range report into
  existing pre-push admission.
- [ ] 2.5 Project declared/armed message and push-range enforcement in status and
  keep `ethos hook install --root <root> --json` as the sole repair action.
- [ ] 2.6 Make GitHub and GitLab integration events invoke the public range owner,
  regenerate provider projections, and retain no provider-local parser or range
  implementation.

## 3. Closure

- [ ] 3.1 Prove repository-wide reference closure: one declaration, compiler,
  range projector, and validator; no old module, duplicate walker, facade,
  policy regex, state store, or historical exception list.
- [ ] 3.2 Run focused hook, commit, admission, status, lifecycle, CI-template,
  SHA-1/SHA-256, Ruff, type, import-boundary, module-layout, and strict OpenSpec
  gates with no warnings.
- [ ] 3.3 Run exact-HEAD full proof, archive the official Change, land through
  candidate and accepted closeout, install and read back the immutable accepted
  runtime, and retire the Work Lane with no ref, worktree, Lease, or active
  Change residue.
- [ ] 3.4 Publish the same accepted commit to every declared remote and observe
  GitHub and GitLab hosted results independently before claiming remote closure.
