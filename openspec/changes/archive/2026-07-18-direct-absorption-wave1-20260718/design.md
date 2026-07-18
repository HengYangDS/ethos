## Context

The accepted root and `candidate/dev` currently share one HEAD, but the
recovered Work Lane cohort still contains diverged, dirty, unbound, and
holder-owned branches. Git ancestry and a clean merge tree can nominate a
comparison candidate; neither proves that an old implementation is correct for
the current contract.

## Design

1. **Classify before replay.** Compare each direct candidate's stated behavior
   and focused regression against the current product and mark it
   current-equivalent, current-missing, deferred, or holder-bound.
2. **Replay behavior, not history.** A current-missing behavior gets a focused
   regression and the smallest implementation on the owned lane. Its historical
   branch remains evidence, not a merge target.
3. **Separate absorption from retirement.** Owned commit, focused proof, parity
   where required, executed proof, candidate land, and accepted closeout prove
   absorption. Only afterwards may the source lane retire through a fresh native
   lifecycle command.
4. **Keep non-admission explicit.** The optional container-contract family is
   retained until a dedicated current product/adopter decision proves admission.
5. **Keep external authority external.** The moving dual-remote successor and
   every valid leased lane remain observe/handoff work.

## Proof Strategy

- Focused CI/runtime, test-harness, Docker-context, build-hook, and coverage
  regressions prove current behavior.
- Strict OpenSpec validation, lifecycle/claim checks, changed-scope planning,
  parity when required, and HEAD-bound proof bind the owned commit.
- A later retirement re-observes the exact source ref, worktree, dirtiness,
  lease, and accepted relation. A changed observation stops the effect.

## Recovery

Recovered source Work Lanes and verified recovery material remain intact until
the corresponding native retirement succeeds. Failure leaves both intact.
