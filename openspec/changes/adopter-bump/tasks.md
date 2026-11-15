# Tasks

## 1. The pin move in the repair plan

- [ ] 1.1 Add the regressions to `tests/unit/cli/test_lane_paradigm_repair.py`. Done when they
      fail before the code for a tree on the `http:ethos` table, on an older bare pin, with no
      pin, with no Mise configuration, with a pin with options, with both forms and under a
      development build, and for the journey of preview, apply and second preview.
- [ ] 1.2 Share adoption's merge of the bare entry as `with_bare_entry` in the repair module.
      Done when the plan rows of `tests/unit/adoption/test_pin.py` pass unchanged.
- [ ] 1.3 Report the selection with `pin_gap`, write it with `pin_move`, and let
      `paradigm_repair_plan` take the handlers that a request adds. Done when the tree rows of 1.1
      pass and no gap's carrier holds anything but the configuration path.
- [ ] 1.4 Add `--pin` to the request and compose the upgrade in `repair_paradigm`. Done when the
      journey of 1.1 passes: one admission names the configuration and the repaired OpenSpec
      rules, the next action is `mise --cd <root> lock`, the actions then name the projection
      step, and a second preview plans no edit and names no step.
- [ ] 1.5 Report a Mise configuration that cannot be read as itself, through the plan's own
      reader. Done when the regression shows a repair that names the file, no edit and no
      admitted path, where the result named the release's bare entry before.

## 2. The block and adoption's next step

- [ ] 2.1 Block a request against a newer selection before any plan, and register
      `runtime_pin_ahead` in the gap table. Done when the regression for both forms passes: the
      preview and the apply block with that gap, name the rerun through Mise and write nothing,
      and the same tree's plan without `--pin` is unchanged.
- [ ] 2.2 Name the move in adoption's conflict. Done when the regression in
      `tests/unit/adoption/test_pin.py` passes: the conflict of an `http:ethos` table and of an
      older bare pin names `ethos lane repair-paradigm --pin --root <root> --json` in a Work Lane,
      and the conflict of a newer pin and of a pin with options does not.
- [ ] 2.3 Continue a retained topic's rename to the pin request. Done when the regression in
      `tests/unit/lanes/test_legacy_role_rename.py` shows `--pin` in the next action of the
      rename's preview and the request's preview after the applied rename.

## 3. Documents and budgets

- [ ] 3.1 Describe the move in `docs/architecture/adoption-profiles.md`, point to it from
      `docs/reference/operational-roots.md` and add the changelog entry under `Added`. Done when
      Prettier and the prose gate accept the three files.
- [ ] 3.2 Measure the source budget. Done when product and tests are at most 170 and 205
      line-equivalents above the lane base, and the decision-density baseline is unchanged.

## 4. Lane, hosted and owner tasks

- [ ] 4.1 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
- [ ] 4.2 Run the first bump through the product on a disposable copy of one governed tree that
      holds the `http:ethos` table: the preview, the apply, the relock with that repository's CI
      Mise and the projection step. Done when the lock holds an attested entry for the pin, the
      run states what the relock did with the lock's older entries, and its minutes are on the
      weekly page.
- [ ] 4.3 Run the blocked request's next action once with a real Mise. Done when
      `mise --cd <root> exec --locked -- ethos lane repair-paradigm --pin --root <root> --json`
      runs the release that the tree selects, or the next action is corrected to the form that
      does.

## Workflow follow-up

- A separate row decides the writer of a bump lane's Change record and changelog line. Until it
  lands, "files written by hand per bump" stays above 0.
