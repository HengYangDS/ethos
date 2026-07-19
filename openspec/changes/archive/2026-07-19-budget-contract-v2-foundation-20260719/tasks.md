## 1. Governance foundation

- [x] 1.1 Accept DR-0008 and update decision indexes, dependencies, and code links.
- [x] 1.2 Complete the design and implementation plans and freeze the v1 baseline,
  current observation, debt inventory, and replay-drift facts.
- [x] 1.3 Keep the active claim and Chronicle digest-bound to this exact Change
  without claiming enforcement change, cutover, or compression completion.

## 2. Behavior-preserving extraction

- [x] 2.1 Move source-budget tests to the new domain owner and verify RED before
  production code exists.
- [x] 2.2 Extract source-budget behavior into
  `ethos.domain.source_budget.core`, update the command provider and scorecard,
  and remove the old owner without a forwarding shim.
- [x] 2.3 Prove equivalent command output, exit status, policy facts, debt
  lifecycle, and required-gap semantics at the same HEAD.
- [x] 2.4 Reconstruct the extraction on a successor based on current candidate
  truth after `refresh_base_failed`, preserving current taxonomy and campaign
  advisory semantics while retaining predecessor history.

## 3. Verification

- [x] 3.1 Run successor focused tests, Python/config/schema checks, claims,
  strict OpenSpec lifecycle, parity, and HEAD-bound executed proof.

## Post-Archive Transition Boundary

Official archive, archive-bound carrier and evidence refresh, final parity and
HEAD-bound proof, candidate landing, accepted-root closeout, local publication
readiness, and owned Work Lane retirement are separate native lifecycle
transitions. Their command receipts determine whether each transition occurred;
remote publication and hosted CI remain separately evidenced boundaries.
