# Report Hard Quality Floor

## Why

`ethos report` is the product scorecard. A product hard quality gap that would
block proof or publication must appear in the report's blocking gap layer rather
than hiding behind a green scorecard.

The existing report hard floor covered size, module layout, product boundary,
and contributor policy. Coverage, type, and public-surface docstring quality
already had standalone owner read models and gates, but report did not consume
those verdicts directly.

## What changes

- Extend the report hard quality floor to consume the existing coverage, type,
  and docstring read models.
- Route their required gaps to `ethos quality coverage --json`,
  `ethos quality types --json`, and `ethos quality docstrings --json`.
- Preserve one command plane and one quality truth boundary: report reads the
  existing gate verdicts; it does not duplicate gate policy or create a new
  store.
