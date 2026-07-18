## Context

`dev` and `candidate/dev` currently point to the same accepted HEAD, while the
repository still exposes a large, mutable cohort of linked foreign Work Lanes
and one unbound Work Lane reference.  A compact reader intentionally defers
foreign worktree state, so it is useful for orientation but is not sufficient
input for a preservation, handoff, replay, or retirement decision.  The full
`ethos lane status --json` reader is the starting point for every decision, and
the target's Git/lease facts are recomputed immediately before an effect.

This Change is the first owned governance carrier.  It does not turn foreign
paths into writable paths and does not perform a foreign-lane effect before its
Chronicle decision is accepted.  It records the audit and bounded successor
plan.  Later owned successor lanes create preservation evidence, replay only
verified residual product behavior, and use native commands for each lifecycle
transition.

## Goals / Non-Goals

**Goals:**

- Give every currently observed `work/*` target one current, exact, reviewable
  disposition: handoff, semantic replay, preserve-retire, retire, or block.
- Define the preservation manifest, patch digest, and target-observation
  obligations that a follow-on successor must satisfy before an irreversible
  action.
- Promote an accepted Chronicle decision that authorizes only exact future
  native effects; each successor still needs its own HEAD-bound proof before
  candidate or accepted-root movement.
- Keep mutable target facts fresh: any change to head, dirty digest, lease
  generation, holder, or target relation invalidates a pending decision.

**Non-Goals:**

- No foreign worktree editing, normalizing legacy leases by invention, raw Git
  cleanup, wildcard retirement, or hidden stash carrier.
- No remote availability assertion, remote reconciliation, push, release, or
  hosted-CI success claim.
- No wholesale merge of historical lane lineages into the current candidate.

## Decisions

1. **Use a two-level observation protocol.** `orient` and `status` provide
   fast root readiness; the complete `lane status` payload and direct
   read-only Git observation provide the exact lane matrix.  A compact reader
   is never used to certify a foreign lane clean or retire-ready.

2. **Preserve before interpretation in a successor.** Any dirty or unbound
   target receives a content-addressed preservation bundle before a successor
   decides whether its semantic delta is already accepted, must be replayed, or
   must remain blocked.  A preservation bundle is evidence, not a transfer of
   mutation authority.

3. **Promote the decision before exceptional ownership paths.** A valid
   cooperative holder uses normal handoff and completes its lane through the
   ordinary lifecycle.  Missing, stale, disputed, or non-mechanical ownership
   uses the accepted Chronicle-backed `lane resolution decide` then `lane
   resolution apply` protocol for one exact branch and one exact current
   observation.  This carrier stops before either command's apply phase.

4. **Replay behavior, not stale topology.** A lane whose intent remains absent
   contributes requirements and focused tests to the owned current-baseline
   implementation.  Its old commits are evidence sources; they are not a
   wholesale merge candidate.

5. **Separate outcomes and evidence planes.** A semantic replay is proven and
   landed through candidate and accepted closeout before its source lane can be
   retired.  Local CI fallback, remote reconciliation, remote push, and hosted
   verification remain separately labelled outcomes.

6. **Apply sequentially and recheck after every effect.** Decisions are
   prepared and applied one lane at a time.  Each apply is preceded by a fresh
   full observation and followed by status/report inspection, which prevents a
   moving leased lane from inheriting a stale `--expect-head`.

## Risks / Trade-offs

- **Foreign holder advances a lane during audit** → Treat observation as stale;
  regenerate the row and do not apply the prior decision.
- **Dirty overlay is accidentally treated as committed history** → Capture both
  Git status provenance and a patch/manifest before semantic comparison.
- **Large cohort delays visible progress** → Use small, receipt-producing
  batches; command output is bounded to a temporary log with an exit code and
  completion timestamp instead of relying on a terminal UI wait state.
- **Old intent conflicts with current product behavior** → Extract a focused
  regression first and retain a blocked/preserved outcome if the current
  contract deliberately supersedes it.
- **Closeout evidence is mistaken for remote release proof** → Keep the
  publication payload in local-readiness mode and do not call remote mutation.

## Migration Plan

1. Freeze a fresh exact matrix in the owned lane and bind it to the claim and
   Chronicle.
2. Validate and archive this decision carrier, then obtain HEAD-bound proof,
   candidate land, and accepted-root closeout without a foreign-lane effect.
3. Start a successor from the accepted decision.  It performs one exact
   preservation, handoff, exceptional-resolution, or semantic-replay unit at a
   time and records the result.
4. Retire only exact lanes whose postconditions hold; retain evidence-bound
   blocked outcomes for everything else.
5. On failure, stop before the affected irreversible command, keep the
   preservation package and decision, and re-observe on the next attempt.
