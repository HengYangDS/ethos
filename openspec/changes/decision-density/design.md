# Design

## Context

See the [proposal](proposal.md). The quality specification's one-owner-per-property rule means a
property is judged once; today two Ruff rules judge branch counts and nothing judges decisions held
in expressions.

## Goals / Non-Goals

Goals:

- New or grown functions above a cognitive complexity of 15 are refused.
- Long Boolean conditions have their own limit, lowered over time.

Non-Goals:

- Refactoring the 342 baseline functions; Phase 2's typed reports and effect plans shrink them.
- A diff against a Git base: the gate stays offline and deterministic over the checkout.

## Decisions

1. The measure is complexipy's `file_complexity`, keyed by repository path and qualified function
   name; two definitions under one key keep the higher score.
2. The baseline is data in `tests/fixtures/`, written by hand or by the test's own failure message,
   never by the gate, so no gate run writes a tracked file.
3. PLR0916 at 23 is a ratchet with a target of 5, not a calibrated pass: the distribution is 67
   conditions over 5, 20 over 8, 12 over 10, 6 over 12, 3 over 15 and 1 over 20.
4. C901 and PLR0912 leave the Ruff selection together with `[lint.mccabe]`; PLR0911 and PLR0915
   stay, since they judge return count and statement count, not decisions.

## Risks / Trade-offs

- complexipy does not traverse every expression position (keyword arguments among them); a planted
  case records what it counts, and PLR0916 covers long conditions.
- The baseline is large; its size falls only through real refactors, which the stale-entry rule
  forces to be recorded.
