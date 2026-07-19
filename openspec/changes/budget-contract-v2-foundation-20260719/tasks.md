## 1. Governance foundation

- [x] 1.1 Accept DR-0008 and update decision indexes, dependencies, and code links.
- [ ] 1.2 Complete the design and implementation plans and freeze the v1 baseline,
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

## 3. Verification and closeout

- [ ] 3.1 Run focused tests, Python/config/schema checks, claims, strict OpenSpec
  lifecycle, parity, and HEAD-bound executed proof.
- [ ] 3.2 Archive through the official OpenSpec CLI, refresh archive-bound claim
  evidence, and rerun proof on the archive HEAD.
- [ ] 3.3 Land to candidate, complete audited accepted-root closeout, evaluate
  local publication readiness, and retire the owned Work Lane as separate
  transitions.
