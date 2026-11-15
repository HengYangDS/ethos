# Tasks

## 1. Regressions

- [x] 1.1 Add `test_adoption_refuses_a_selection_as_activation_does_and_names_its_repair` to
      `tests/unit/adapters/repo/runtime/test_pin_selection.py`, with one case for each refusal: an
      unattested pin, a pin that is not installed, an install that refuses the declaration and a
      damaged install. Done when the first three fail without task 2 (two on the next action, one
      because a refused selection reached materialization) and the fourth passes. Evidence: lane
      commits `7c625c6a7` and `e657aedaa`; in the preparation clone on the base's product code the
      first three cases failed and the fourth passed.
- [x] 1.2 Add the cases `no-file`, `unparsable`, `both-keys` and `dotted-key` to
      `test_an_exit_removes_only_the_pin_that_adoption_wrote` in `tests/unit/adoption/test_pin.py`.
      Done when the last three fail without task 2 because the plan names no pin. Evidence: lane
      commit `7c625c6a7`. In the preparation clone on the base's product code `unparsable` and
      `dotted-key` failed, and a direct call of the base's reader returned no pin for `both-keys`.
      The six cases pass in the lane (213 tests of eleven test targets at `e657aedaa`, 01:59:31).
- [x] 1.3 Assert the applied result's next action and its kind in the same test. Done when the three
      kept cases fail without task 2.5 on the bare status command. Evidence: lane commit
      `e657aedaa`; the three kept cases failed on the bare status command in the preparation clone
      (3 failed, 7 passed).

## 2. Repairs

- [x] 2.1 Continue a refused runtime selection with the refusal's own next action in
      `src/ethos/application/adoption.py`. Done when the cases `unattested` and `not-installed` pass
      and `adopt_existing` keeps its decision density. Evidence: lane commit `7c625c6a7`; the cases
      pass in the lane run that task 1.2 names, and the decision density guard passed at `ec33ac087`
      (02:18:43).
- [x] 2.2 Add `require_accepting_runtime` beside `rollback_preflight`, call it from `_runtime_plan`
      and from `_supply_selection`, and point the three test patches of the two calls at the
      rollback module. Done when the case `declaration-repaired` passes for the preview and the
      apply with no selector written, and
      `test_activation_selects_the_pinned_install_and_a_lane_rolls_back_with_a_receipt` and
      `test_a_refused_rollback_leaves_no_effect` pass. Evidence: lane commit `e657aedaa`; the pin
      selection, rollback, activation and hook command modules passed in the lane run that task 1.2
      names.
- [x] 2.3 End `RESTORE_ACTION` with the request instead of the installation. Done when the tests
      that compare the constant pass. Evidence: lane commit `7c625c6a7`; the rollback preflight
      tests passed at 02:12:43.
- [x] 2.4 Name a kept configuration in `_pin` and write the Mise configuration in `_apply_fenced`
      only when the plan names `after`. Done when all six cases of task 1.2's test pass. Evidence:
      lane commit `7c625c6a7`; the lane run that task 1.2 names.
- [x] 2.5 Name a kept configuration and its reason in the applied exit's next action, before the
      status command. Done when the three kept cases of task 1.3 pass and `_apply_fenced` keeps its
      decision density. Evidence: lane commit `e657aedaa`; the lane run that task 1.2 names.
- [x] 2.6 Give `runtime_rollback_probe_failed` its row in the gap registry, now that adoption can
      also report it. Done when the rollback preflight tests require a row for every gap that the
      preflight raises, having failed for this one without the row. Evidence: lane commit
      `1a3b14712`. Without the row five cases failed (5 failed, 6 passed, 02:12:20); with it the
      preflight tests and two registry guards passed 29 tests at 02:12:43.

## 3. Documents

- [x] 3.1 Add the `runtime-activation` delta. Done when
      `openspec validate adoption-pin-repairs --strict` passes. Evidence: lane commit `62c035e81`;
      at `da63d1e11` the static precheck passed with no finding at 02:24:07, which validates every
      active Change strictly.
- [x] 3.2 State the kept pin in `docs/architecture/adoption-profiles.md` and add two `Fixed` entries
      to `CHANGELOG.md` under `[Unreleased]`. Done when Prettier accepts both files. Evidence: lane
      commits `7c625c6a7` and `e657aedaa`; Prettier accepted both files at each commit.

## 4. Lane, hosted and owner tasks

- [x] 4.1 Lane: apply the patch under a passing `ethos lane prewrite` and commit it. Done when the
      lane head holds every path of the patch. Evidence: lane commits `62c035e81`, `7c625c6a7`,
      `e657aedaa` and `1a3b14712`, each under a passing prewrite.
- [x] 4.2 Lane: run the prose gate on the changed Markdown. Done when Vale and codespell report no
      finding. Evidence: Vale accepted the changed Markdown at each commit, codespell reported no
      finding on it at `7c625c6a7`, and the prose gate is among the gates of the readiness run:
      readiness passed 28 gates with none failing at 03:26:10.
- [x] 4.3 Lane: pass the precheck and readiness at the lane head. Done when each passes on the
      committed head. Evidence: at `da63d1e11` the static precheck passed with no finding at
      02:24:07, and readiness passed 28 gates with none failing at 03:26:10.
