# Proposal

## Why

Ruff's C901 and PLR0912 count statement branches only. ETHOS code keeps many decisions in Boolean
operators and conditional expressions, which neither counts: `inspect_status` in
`src/ethos/application/inspection.py` has a C901 value of 3 and 26 Boolean operators, 20
conditional expressions and 182 lines. Measured with complexipy 8.3.0 at `c89ac1884`, 342 of 3,445
functions in `src/` and `tools/` exceed a cognitive complexity of 15 while C901 at 10 reports none.
Cognitive complexity also counts a run of like Boolean operators once, so a single `if` that joins
23 conditions (`src/ethos/contracts/gates.py:94`) needs a second measure: Ruff's PLR0916 finds 67
`if` statements with more than 5 Boolean expressions.

## What Changes

- complexipy, a maintained MIT tool, owns cognitive complexity. One architecture test measures every
  function in `src/` and `tools/` through its Python API and refuses any function above 15 unless a
  pinned baseline names it with a score it does not exceed. The baseline lists the 342 current
  functions and only shrinks: an entry whose function improved or disappeared fails until removed.
- Ruff's PLR0916 is selected by exact code with `max-bool-expr = 23`, the measured maximum, as the
  ratchet whose target is 5; typed reports, which replace hand-written payload validation, lower it.
- C901 and PLR0912 retire, so one owner judges each property.
- complexipy joins the `dev` dependency group under the 24-hour release-age rule.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. ETHOS's own quality configuration changes; no requirement changes.

## Impact

`pyproject.toml`, `uv.lock`, `.config/checks/ruff/ruff.toml`,
`tests/architecture/test_decision_density.py`, `tests/fixtures/decision-density-baseline.json` and
the CI supply image binding.
