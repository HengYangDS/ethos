---
subject: ethos:decision:product-budget-step
role: decision
state: canonical
decision_id: DR-0020
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/quality/spec.md
---

# DR-0020: The Product Ceiling Moves to 80,000 for the RC Work

Status: canonical rationale. The native source-budget declaration owns the number.

Date: 2026-11-07.

Purpose: preserve the necessity review that moved the product ceiling one 5,000 step, what was
removed first, and when to look again.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md)
and the `product-budget-step` and `rc-plan` OpenSpec Changes.

## Context

After DR-0019 the product measures 73,163 of its 75,000 line-equivalent ceiling. The 2026-11-07
expert committee made three families of Changes RC-blocking. Their converged designs estimate about
1,980 product line-equivalents for the operation catalog, about 440 for the unified installation
(`github-pin` step 2) and about 460 for the release rehearsal: about 2,880 together, which ends near
76,000. DR-0010 allows one 5,000 step only after the growing owner retires proved duplication and
superseded mechanics, and the owner's 2026-11-01 rule lets the agent take that step with evidence.

## Decision

- **Removed first.** One owner now reads the process actor (47 direct reads in 32 modules, 12
  inlined defaults and 4 unnormalized reads before); one module checks hexadecimal identities (18
  procedural copies before); the dead `mapped_retag_receipt` is gone. In all, 61 replacements in 43
  modules took the product from 517,571 to 517,273 code tokens, 73,121 line-equivalents.
- **What still needs the space.** The catalog's application package, lane operations, run handles,
  hosted observation, delegation authority and MCP projection; the installation pin, its selection
  and its release acceptance; the rehearsal's predecessors, admission and stable path. Each is an
  RC obligation of the committee's resolution, not an optional feature.
- **Why not more removal now.** The larger reductions are structural: typed facts into pure
  decisions, a Git port that replaces patched Git calls, and retiring text continuations once every
  reader uses the structured next step. They are 0.3.0 work in the catalog design; doing them before
  the RC would re-architect the product under release pressure.
- **The step.** The product ceiling moves one step, from 75,000 to 80,000 line-equivalents.

## Alternatives Rejected

- **Fit the RC under 75,000 by converting text builders first:** it sequences product work by the
  budget, which the committee rejected in round 1, and the conversion depends on the catalog it would
  delay.
- **Compress or relabel:** invalid repairs under the PDC and DR-0019.
- **Two steps at once:** DR-0010 allows one reviewed step at a time.

## Consequences and Boundary

- The RC families have about 6,900 line-equivalents of space against about 2,880 planned.
- This record admits no growth by itself; each later step needs its own review.

## Evidence and Revisit

Measurements: the lane's source-budget report before and after the removal (`product-budget-step`
tasks). Revisit when the RC families land with more than 2,000 line-equivalents to spare, so the
ceiling can return toward the measured size, or when the product reaches 78,000 before the 0.3.0
reductions.
