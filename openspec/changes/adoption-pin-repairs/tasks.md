# Tasks

## 1. Regressions

- [ ] 1.1 Add `test_adoption_refuses_a_selection_as_activation_does_and_names_its_repair` to
      `tests/unit/adapters/repo/runtime/test_pin_selection.py`, with one case for each refusal:
      an unattested pin, a pin that is not installed, an install that refuses the declaration and
      a damaged install. Done when the first three fail without task 2 (two on the next action,
      one because a refused selection reached materialization) and the fourth passes.
- [ ] 1.2 Add the cases `no-file`, `unparsable`, `both-keys` and `dotted-key` to
      `test_an_exit_removes_only_the_pin_that_adoption_wrote` in `tests/unit/adoption/test_pin.py`.
      Done when the last three fail without task 2 because the plan names no pin.
- [ ] 1.3 Assert the applied result's next action and its kind in the same test. Done when the
      three kept cases fail without task 2.5 on the bare status command.

## 2. Repairs

- [ ] 2.1 Continue a refused runtime selection with the refusal's own next action in
      `src/ethos/application/adoption.py`. Done when the cases `unattested` and `not-installed`
      pass and `adopt_existing` keeps its decision density.
- [ ] 2.2 Add `require_accepting_runtime` beside `rollback_preflight`, call it from
      `_runtime_plan` and from `_supply_selection`, and point the three test patches of the two
      calls at the rollback module. Done when the case `declaration-repaired` passes for the
      preview and the apply with no selector written, and
      `test_activation_selects_the_pinned_install_and_a_lane_rolls_back_with_a_receipt` and
      `test_a_refused_rollback_leaves_no_effect` pass.
- [ ] 2.3 End `RESTORE_ACTION` with the request instead of the installation. Done when the tests
      that compare the constant pass.
- [ ] 2.4 Name a kept configuration in `_pin` and write the Mise configuration in `_apply_fenced`
      only when the plan names `after`. Done when all six cases of task 1.2's test pass.
- [ ] 2.5 Name a kept configuration and its reason in the applied exit's next action, before the
      status command. Done when the three kept cases of task 1.3 pass and `_apply_fenced` keeps
      its decision density.

## 3. Documents

- [ ] 3.1 Add the `runtime-activation` delta. Done when
      `openspec validate adoption-pin-repairs --strict` passes.
- [ ] 3.2 State the kept pin in `docs/architecture/adoption-profiles.md` and add two `Fixed`
      entries to `CHANGELOG.md` under `[Unreleased]`. Done when Prettier accepts both files.

## 4. Lane, hosted and owner tasks

- [ ] 4.1 Lane: apply the patch under a passing `ethos lane prewrite` and commit it. Done when the
      lane head holds every path of the patch.
- [ ] 4.2 Lane: run the prose gate on the changed Markdown. Done when Vale and codespell report no
      finding.
- [ ] 4.3 Lane: pass readiness and the proof at the lane head. Done when both pass on the
      committed head.
