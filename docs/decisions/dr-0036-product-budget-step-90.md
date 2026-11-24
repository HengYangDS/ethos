---
subject: ethos:decision:product-budget-step-90
role: decision
state: canonical
decision_id: DR-0036
decision_status: accepted
date: 2026-11-24
relations:
  current_owner: ../../openspec/specs/quality/spec.md
  updates: DR-0025
---

# DR-0036: The Product Ceiling Moves to 90,000, Decided Before Its Review

Purpose: preserve why the product ceiling moved one more 5,000 step, that the owner decided the
step before the necessity review was made, what that review found afterwards, and when to look
again.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md),
[DR-0025: The product ceiling moves to 85,000 for the common rules](dr-0025-product-budget-step-85.md),
whose step and whose revisit point this record replaces, and the `product-budget-step-90` OpenSpec
Change.

## Context

DR-0025 asked for a review when the product reaches 83,000 line-equivalents before the 0.3.0
reductions. That point was passed without one. On 2026-11-24, after the repair of the locked tool
install landed, accepted `dev` read 84,888 of 85,000, with 112 free. Three pieces of
approved work wait for space: the first accepted branch of a repository adopted from its release
branch, the second half of the host queue layer, and the command of the known-defect carrier.

DR-0010 allows one 5,000 step only after the growing owner retires proved duplication and
superseded mechanics, and the owner's rule of 2026-11-01 asks for that removal first. On 2026-11-24
the session that builds the product told the owner that this review had not been made and
proposed to decide the step two days later with it. The owner decided the step that day.

## Decision

- **The step.** The product ceiling moves one step, from 85,000 to 90,000 line-equivalents. The
  owner decided it on 2026-11-24, for this step only.
- **The order was reversed, once.** The decision came before the review. This record does not
  change DR-0010 or the rule of 2026-11-01: the next step needs its review first.
- **The review, made the same day after the decision.** A search of the whole product for
  top-level definitions that no tracked file names again found one, a refusal code's constant
  that nothing raises, which is removed with the step. A search for structurally identical
  function bodies of three or more statements found none.
- **Why not more removal now.** The larger reductions stay structural, as DR-0020 and DR-0025
  found: typed facts into pure decisions, a Git port, and retiring text continuations. They
  remain 0.3.0 work.

## Alternatives Rejected

- **Decide at the weekly cut with the review in hand:** the proposal of the session that builds
  the product. The owner decided earlier; the first accepted branch then starts two days sooner.
- **Fit the first accepted branch into the 112 free and take the step later:** measured on its
  patch it needs 84, which fits, and leaves 28 for the two pieces that follow.
- **Compress or relabel:** invalid repairs under the product design contract and DR-0019.

## Consequences and Boundary

- This record admits no growth by itself; each later step needs its own review, made first.
- The tests and the tools keep their ceilings. The tests read 114,272 of 115,000 on the same
  day, past the revisit point of DR-0033; that review is a decision of its own.
- Of DR-0025, this record replaces the step and the revisit point. Its review, its rejected
  alternatives and its other consequences stand as written.

## Evidence and Revisit

The repository's owner decided the step on 2026-11-24. Measurements: the source-budget readings
of that day at accepted `dev` and at the lane head, the two product searches named above, and the
measured size of the first accepted branch's patch, as the `product-budget-step-90` tasks record
them. Revisit when the product reaches 88,000 before the 0.3.0 reductions, or when they land.
