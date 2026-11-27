# Proposal

## Why

Six release entries, from 0.2.0-beta.6 to 0.2.0-beta.11, name the same limit under "Not qualified
by this beta": "a rollback after the declaration repair, which the journey reports as
`not_qualified`". The journey's receipt writes that value as a constant in
`tools/ci/delivery/acceptance/runtime.py`; no step of the journey computes it.

This row is to end that limit. The archived `rc-plan` design gives the row its content and its
place: appendix B.3 states four steps of restore-then-rollback for each predecessor, B.8 lists the
Change as item 8, "`rollback-after-repair`, B.3's four steps", and decision 2, family 7, sizes and
orders it: "`rollback-after-repair` (B8; 0/+80/+130) follows B2 and C2". B2 is `hermetic-journey`,
which this Change's base holds, and C2 is `pin-selection`, archived on 2026-11-15. The archived
`rc-scope-plan` design listed the row under the frozen batch; the committee's resolution of
2026-11-14, whose rules DR-0029 records, reads it in the batch of 0.2.0-beta.13.

The four steps were written on 2026-11-07, before `pin-selection` gave a departure from the pin
its receipt and before `hermetic-journey` took Mise and the network out of the journey's
qualification. Read against this Change's base, step by step:

- The product does steps 2, 3 and 4. The real hook activation, run in process on the fixture
  runtimes of the product's own rollback tests, gives the refusal with and without a reason, the
  receipt, the open state and the receipt's deletion. Two names differ from the plan: the open
  state is `runtime_selection_open`, and the transition after the landed revert deletes the
  receipt, not the landing.
- The journey cannot run the steps as they are written. Its qualification has no Mise on its path,
  so a landed pin bump is not followed there; its installations are not keyed by the pin; its
  acceptance package has no function that lands; and the receipt first ships in 0.2.0-beta.11, so
  no subject that the base knows as published has it.
- The refusal of step 2 has no predecessor left to give it. Only a release before 0.2.0-beta.6
  refuses a repaired declaration, and every release since reads one. On the releases that
  governed repositories select today, the product admits a rollback after the repair.

So the limit that the entries name is narrower than the plan's steps, and the plan's steps are
wider than this row's size. The design reads them as three slices.

## What Changes

This Change is a draft: it holds this proposal and the design, and no tasks.

- **The first slice, proposed for this row.** After the retained upgrade and its repair, the
  journey asks the successor's console, from the repaired lane, to select the predecessor that the
  repository holds as its rollback. The receipt records what the product decided: `admitted`, with
  the predecessor selected, the retained state equal and the successor selected again; or
  `refused`, with `runtime_rollback_declaration_repaired` and nothing changed. In the journey's
  receipt the key `rollback_after_declaration_repair` holds that result. The install smoke shares
  the upgrade function and keeps the constant.
- **The named remainder.** A receipted rollback in a fixture that declares a pin, and a pin that
  is followed across landings, are named `not_qualified` in the same result, each by its own key,
  until their slices land.
- The release guide's step on what a beta does not qualify and the changelog say what changed, and
  the next release entry replaces its line with the narrower ones.

Nothing changes for a governed repository. The Change touches the journey's tools and tests and
no product code, and it adds no gap and no refusal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Decision 6 of the design says
why the first slice needs no delta and which requirement the later slices change.

## Impact

One new module in `tools/ci/delivery/acceptance/` and its call in `journey.py`; one test module in
`tests/unit/ci/delivery/`; the release guide and `CHANGELOG.md`. The design gives the sizes with
their sources: about 100 tool line-equivalents, measured on a sketch that was not run, and an
estimated 80 to 110 test line-equivalents, against the row's 130 and 80. The estimated cost in the
journey's time is 10 to 28 seconds for each predecessor on each leg.

The changed journey is a harness, so it is not ready when its unit tests pass. One dispatch of the
hosted workflow, with a journey tag and its predecessor, runs it end to end.

Owner: the release lead. Next action: answer the design's open questions, then write the tasks.
Read again: at the cut of 0.2.0-beta.13.
