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
2. The baseline is data in `tests/fixtures/`, written by hand from the measured `scores()`, never by
   the gate, so no gate run writes a tracked file.
3. PLR0916 at 23 is a ratchet with a target of 5, not a calibrated pass: the distribution is 67
   conditions over 5, 20 over 8, 12 over 10, 6 over 12, 3 over 15 and 1 over 20.
4. C901 and PLR0912 leave the Ruff selection together with `[lint.mccabe]`; PLR0911 and PLR0915
   stay, since they judge return count and statement count, not decisions.

## Risks / Trade-offs

- complexipy 8.3.0 skips decisions inside keyword arguments, lambdas, f-strings, subscripts and
  `yield`: at `c89ac1884`, 541 of 6,847 conditional expressions and Boolean operations in `src/`
  and `tools/`, in 248 functions, sit there. A planted case pins that a keyword-argument decision
  scores 0, so the upgrade that counts them fails it and must re-pin the baseline. complexipy's
  main fixed the gap after 8.3.0
  ([rohaquinlop/complexipy#335](https://github.com/rohaquinlop/complexipy/pull/335), merged on
  2026-11-05); no release ships it yet. PLR0916 covers long `if` conditions.
- The baseline is large; its size falls only through real refactors, which the stale-entry rule
  forces to be recorded.
