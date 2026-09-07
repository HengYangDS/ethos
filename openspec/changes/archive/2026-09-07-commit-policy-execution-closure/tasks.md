## 1. Contract And RED

- [x] 1.1 Strictly validate the four modified capability deltas and confirm the
  design contains no unresolved authority, range, trust, or migration decision.
- [x] 1.2 Add failing tests for index-bound `commit-msg` admission, including a
  malformed staged policy, a changed staged policy, and an invalid raw Git
  commit subject.
- [x] 1.3 Add failing tests for introduced-range admission covering fast-forward,
  non-fast-forward, new proposal, absent or non-ancestor baseline, SHA-1,
  SHA-256, annotated-tag peeling, deletion, multiple updates, malformed or absent
  tip policy, invalid subject, missing/wrong-format signature, and old-history
  exclusion.
- [x] 1.4 Add failing command, hook activation, status, and dual-provider
  projection tests proving all transports invoke the same public owner.

## 2. Unique Owner And Deletion

- [x] 2.1 Create the semantic commit adapter package, move lifecycle creation
  and signing into its creation owner, and delete `git_signing.py` without a
  facade.
- [x] 2.2 Implement one tip-policy, endpoint-peeling, introduced-range, and
  commit-validation owner; retain optional local trust verification for
  lifecycle effects.
- [x] 2.3 Make configured author/committer identity consume the shared revision
  sequence and delete its range walker and duplicate ancestry helper.
- [x] 2.4 Install and execute `commit-msg`, expose the named-coordinate
  `ethos hook commit-range` JSON command, and compose the range report into
  existing pre-push admission.
- [x] 2.5 Project declared/armed message and push-range enforcement in status and
  keep `ethos hook install --root <root> --json` as the sole repair action.
- [x] 2.6 Make GitHub and GitLab integration events invoke the public range owner,
  regenerate provider projections, and retain no provider-local parser or range
  implementation.
- [x] 2.7 Reuse an exact valid selected runtime before Python-image provisioning,
  while forcing fresh materialization whenever build, manifest, platform,
  architecture, dependency-lock, or retained-wheel identity differs.
- [x] 2.8 Advance the one product-version authority for the new accepted
  behavior, synchronize its npm projections, and bind prepared Node supply only
  to the installed `node_modules/*` dependency closure.
- [x] 2.9 Make the existing local toolchain bootstrap admit or provision one
  shared exact-version native Python image before offline runtime activation;
  keep activation itself free of installation and fallback behavior.
- [x] 2.10 Apply the global deep-module obligation through the existing product
  contract, layout rule, and terminal route; hide commit-policy implementation
  steps, consolidate object judgment, and test complete replay admission without
  duplicating its algorithm in lifecycle callers or tests.

## 3. Pre-Archive Verification

- [x] 3.1 Prove repository-wide reference closure: one declaration, compiler,
  range projector, and validator; no old module, duplicate walker, facade,
  policy regex, state store, or historical exception list.
- [x] 3.2 Run focused hook, commit, admission, status, lifecycle, CI-template,
  SHA-1/SHA-256, version, Node-supply, bootstrap-provisioning, Ruff, type,
  import-boundary, module-layout, and strict OpenSpec gates with no warnings.

Completion of these implementation tasks is not delivery completion. Exact-HEAD
full proof remains a mandatory precondition of the public archive operation;
the previous proof at `bed87c044` failed the unchanged 93% coverage floor.
Archive/reproof, candidate/accepted CAS, immutable runtime readback, Work Lane
retirement, same-object publication, and independent hosted observation remain
uncompleted obligations in the existing
[terminal route](../../../docs/plans/terminal-governance-product-design.md#bounded-change-convergence-route).
They cannot be prerequisites checked off before the archive that enables them.
