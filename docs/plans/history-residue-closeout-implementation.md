---
subject: ethos:history-residue-closeout-implementation-20260719
role: plan
state: active
relations:
  implements: history-residue-closeout-20260719
  derives_from: docs/plans/history-residue-closeout-design.md
---

# History Residue Closeout Implementation Plan

Status: active successor-v2 closeout.

Purpose: execute the bounded tracked cleanup defined by the
[OpenSpec change](../../openspec/changes/history-residue-closeout-20260719/) and
[design](history-residue-closeout-design.md).

## Global Constraints

- Work only in the owned successor-v2 Work Lane with
  `ETHOS_ACTOR=agent:openai:thread:root`.
- Run `ethos status --json` and `ethos lane prewrite` before tracked mutation.
- Use the repository runner for ETHOS commands and HEARTBEAT for long commands.
- Do not use stash, hand rebase, compatibility aliases, or writes to protected or
  foreign worktrees.
- Do not apply real local-state maintenance or delete leases, proofs, recovery
  sources, or historical claims without explicit evidence.
- Do not treat source-budget campaign advice as terminal completion.

## Phase 1: Replay And Semantic Repair

- [x] Replay predecessor semantic commits except stale parity evidence.
- [x] Preserve candidate `HookAdmissionRequest` semantics.
- [x] Prohibit redundant `SCHEMA_VERSION` aliases and compatibility wrappers.
- [x] Restore fail-closed Rules migration behavior with a public regression test.

## Phase 2: Scope And Evidence Reconciliation

- [x] Restore 29 claims deleted without retirement evidence.
- [x] Update the three provider-related claims to their current bounded states.
- [x] Reconcile proposal, design, tasks, five deltas, Chronicle, and claim digest.
- [x] Record exact source-budget observation and no-real-apply boundary.

## Phase 3: Verification And Candidate Refresh

- [ ] Run focused rules, scaffold, local-state, receipt, closeout, and quality tests.
- [ ] Run strict claims and OpenSpec validation.
- [ ] Run the complete configured quality and test floor.
- [ ] Execute official `lane refresh-base` against the latest candidate.
- [ ] Regenerate and commit generic parity at the refreshed HEAD.

## Phase 4: Proof And Local Closeout

- [ ] Run HEAD-bound executed proof.
- [ ] Archive the OpenSpec carrier and inspect canonical-spec fusion.
- [ ] Rerun proof on the archived HEAD.
- [ ] Land to candidate and perform accepted-root closeout.
- [ ] Verify local publication readiness and local CI/install evidence.

## Phase 5: Separate Publication Evidence

- [ ] Refresh remote topology and tracking state.
- [ ] Publish only the configured submit/protected branch permitted by policy.
- [ ] Verify hosted CI without treating local fallback as hosted execution.
- [ ] Retire the successor-v2 lane through the official lifecycle.
