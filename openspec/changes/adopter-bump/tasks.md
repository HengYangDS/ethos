# Tasks

## 1. The pin move in the repair plan

- [x] 1.1 Add the regressions to `tests/unit/cli/test_lane_paradigm_repair.py`. Done when they
      fail before the code for a tree on the `http:ethos` table, on an older bare pin, with no
      pin, with no Mise configuration, with a pin with options, with both forms and under a
      development build, and for the journey of preview, apply and second preview.
- [x] 1.2 Share adoption's merge of the bare entry as `with_bare_entry` in the repair module.
      Done when the plan rows of `tests/unit/adoption/test_pin.py` pass unchanged.
- [x] 1.3 Report the selection with `pin_gap`, write it with `pin_move`, and let
      `paradigm_repair_plan` take the handlers that a request adds. Done when the tree rows of 1.1
      pass and no gap's carrier holds anything but the configuration path.
- [x] 1.4 Add `--pin` to the request and compose the upgrade in `repair_paradigm`. Done when the
      journey of 1.1 passes: one admission names the configuration and the repaired OpenSpec
      rules, the next action is `mise --cd <root> lock`, the actions then name the projection
      step, and a second preview plans no edit and names no step.
- [x] 1.5 Report a Mise configuration that cannot be read as itself, through the plan's own
      reader. Done when the regression shows a repair that names the file, no edit and no
      admitted path, where the result named the release's bare entry before.

## 2. The block and adoption's next step

- [x] 2.1 Block a request against a newer selection before any plan, and register
      `runtime_pin_ahead` in the gap table. Done when the regression for both forms passes: the
      preview and the apply block with that gap, name the rerun through Mise and write nothing,
      and the same tree's plan without `--pin` is unchanged.
- [x] 2.2 Name the move in adoption's conflict. Done when the regression in
      `tests/unit/adoption/test_pin.py` passes: the conflict of an `http:ethos` table and of an
      older bare pin names `ethos lane repair-paradigm --pin --root <root> --json` in a Work Lane,
      and the conflict of a newer pin and of a pin with options does not.
- [x] 2.3 Continue a retained topic's rename to the pin request. Done when the regression in
      `tests/unit/lanes/test_legacy_role_rename.py` shows `--pin` in the next action of the
      rename's preview and the request's preview after the applied rename.
- [x] 2.4 Keep `--pin` in the next action of a rename that stopped part way. Done when an
      interrupted rename under `--pin --apply` reports `partial_transition` and names the
      apply with `--pin`, that apply finishes the rename and names the preview with `--pin`,
      and a refused rename under `--pin` changes no content.

## 3. Documents and budgets

- [x] 3.1 Describe the move in `docs/architecture/adoption-profiles.md`, point to it from
      `docs/reference/operational-roots.md` and add the changelog entry under `Added`. Done when
      Prettier and the prose gate accept the three files.
- [x] 3.2 Measure the source budget. Done when the Change's commits are measured against their
      parents: the integration is at most 170 product and 205 tests line-equivalents (169.1 and
      204.7), the four review repairs are stated beside it (17.0 and 60.7; 186.0 and 265.4 in all),
      the lane stays under its three ceilings, and no decision-density entry of this Change's
      functions changed.

## 4. Lane, hosted and owner tasks

- [ ] 4.1 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
- [x] 4.2 Hand the first bump through the product to the first release that carries `--pin`. Done
      when the Workflow follow-up names the run on a disposable copy of one governed tree that holds
      the `http:ethos` table and the three results it owes.
- [x] 4.3 Run the blocked request's next action once with a real Mise on a disposable copy of a tree
      that selects a published release. Done when
      `mise --cd <root> exec --locked -- ethos lane repair-paradigm --pin --root <root> --json` is
      answered by the release that the tree selects (a release older than `--pin` answers by
      refusing the option), or the next action is corrected to the form that does.

## Workflow follow-up

- A separate row decides the writer of a bump lane's Change record and changelog line. Until it
  lands, "files written by hand per bump" stays above 0.
- After the first release that carries `--pin` is published: run the first bump through that release
  on a disposable copy of one governed tree that holds the `http:ethos` table (the preview, the
  apply, the relock with that repository's CI Mise and the projection step). Record the lock's
  attested entry for the pin, what the relock did with the lock's older entries, and the run's
  minutes on the weekly page.
- After two releases carry `--pin`, block a request of the older one on a tree that selects the
  newer one and run the named next action; record that the newer release answers.
