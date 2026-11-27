# Tasks

## 1. The leg after the repair

- [x] 1.1 Add the leg as its own module of the journey's acceptance tools: from the retained
      adopter's one Work Lane, ask the successor's console to select the runtime that the
      repository holds as its rollback, and return `admitted` or `refused` under
      `rollback_after_declaration_repair`, with `receipted_rollback` and `pin_across_landings` as
      `not_qualified`. Done when a test with doubled product readers gets `admitted` after two
      requests (the held runtime, then the successor) with the selector back on the successor,
      and `refused` after one request with nothing changed.
      (In a clone of `3c6260017`: `test_an_admitted_rollback_selects_the_held_runtime_and_returns`
      and `test_a_refused_rollback_is_recorded_when_nothing_changed` pass.)
- [x] 1.2 Fail the leg for every other outcome, with the product's own answer in the message: no
      Work Lane, no held runtime, a refusal that changed state, any other gap, an admitted
      rollback that changed retained state, and no way back to the successor. Done when one test
      case for each raises its `package_rollback_after_repair_*` message.
      (`test_any_other_outcome_fails_the_leg`, 6 cases, passes; with the state check of a refusal
      removed, its case fails.)
- [x] 1.3 Call the leg from the journey's upgrade step after the retained upgrade and let its
      result replace the upgrade's constant; the install smoke keeps the constant. Done when a
      test of the upgrade step returns the leg's decision in place of `not_qualified`, and the
      journey's existing tests pass.
      (`test_the_journey_replaces_the_upgrade_constant_with_the_decision` passes and fails with
      the call removed; the 35 cases of `tests/unit/ci/delivery/test_journey.py` pass.)

## 2. Documents

- [x] 2.1 Say in the release guide's step on what a beta does not qualify, and in the changelog,
      that the rollback after the declaration repair is now decided by the journey, and name the
      two limits that remain. Done when both texts name `receipted_rollback` and
      `pin_across_landings` as not qualified and the documentation checks pass.
      (The release guide's step 5 and the unreleased changelog entry name both limits; the static
      pre-check, documentation gates included, passes at `0ec07e9e2`.)

## 3. Lane, hosted and owner tasks

- [ ] 3.1 Run the tests of tasks 1.1 to 1.3 on Python 3.12 and 3.13. Done when each
      interpreter's result line is in the lane's record.
- [ ] 3.2 Dispatch the release journey of the ref that holds this Change with `journey_tag`
      `v0.2.0-beta.11` and `journey_previous` `v0.2.0-beta.10`. Done when every declared leg's
      receipt holds `admitted` or `refused` under `rollback_after_declaration_repair`, and the
      lane's record names each leg's value and the seconds that the stage took.
- [x] 3.3 Replace the line of the next release entry that names the rollback after the
      declaration repair as not qualified with the two narrower limits. Done when the entry
      names them and no entry says that this rollback is not qualified.
      (The unreleased entry names `receipted_rollback` and `pin_across_landings`, and no line of it
      calls this rollback not qualified; the released entry of 0.2.0-beta.12 is frozen.)
