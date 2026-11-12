---
subject: ethos:decision:product-budget-step-85
role: decision
state: canonical
decision_id: DR-0025
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/quality/spec.md
---

# DR-0025: The Product Ceiling Moves to 85,000 for the Common Rules

Status: canonical rationale. The native source-budget declaration owns the number.

Date: 2026-11-12.

Purpose: preserve the necessity review that moved the product ceiling one more 5,000 step, what
was removed first, and when to look again.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0020: The product ceiling moves to 80,000 for the RC work](dr-0020-product-budget-step.md) and
the `product-budget-step-85` OpenSpec Change.

## Context

Readiness at the lane head of 2026-11-12 measured 80,175 product line-equivalents against the
80,000 ceiling. DR-0020 asked for a review when the product reached 78,000 before the 0.3.0
reductions. The growth since then is the work that DR-0020 counted and the owner's rules of
2026-11-12: one blank-line rule for Markdown lists, an acting owner for canonical text, an opening
docstring for every package marker, and a foundation starter that passes its own paradigm.

## Decision

- **Removed first.** The three pre-commit layout checks of that day read the same staged blobs in
  three loops; one module now reads each file once, which removed 45 line-equivalents. A search of
  the whole product for top-level definitions that no tracked file names again found one,
  `binds_custody`, which is deleted. A search for structurally identical function bodies found
  three groups, and each is intended: the typed SDK facades of `adopt`, `land` and `publish`, the
  typing overloads of `run_git`, and two named path selectors of the layout policy.
- **What still needs the space.** The rules above, which every governed repository receives, and
  the RC families that DR-0020 listed.
- **Why not more removal now.** The larger reductions stay structural, as DR-0020 found: typed facts
  into pure decisions, a Git port, and retiring text continuations. They remain 0.3.0 work.
- **The step.** The product ceiling moves one step, from 80,000 to 85,000 line-equivalents.

## Alternatives Rejected

- **Drop one of the owner's rules to fit:** the owner asked for each of them, and each closes a gap
  that no gate covered.
- **Compress or relabel:** invalid repairs under the product design contract and DR-0019.

## Consequences and Boundary

- This record admits no growth by itself; each later step needs its own review.

## Evidence and Revisit

Measurements: the lane's source-budget report before (80,175) and after the merge (80,130), and the
two product searches named above. Revisit when the product reaches 83,000 before the 0.3.0
reductions, or when they land.
