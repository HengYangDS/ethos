# Tasks

## 1. The state and its two readers

- [x] 1.1 Declare `reporting` in the paradigm and its model. Done when the declaration loads and
      the paradigm's declaration tests pass.
- [x] 1.2 Split the report: every gap under `gaps`, armed ones under `required_gaps`, the rest
      under `reported_gaps`, the next action from the armed ones. Done when
      `tests/unit/repository/test_paradigm_next_action.py` passes with its reporting and armed
      cases.
- [x] 1.3 Make `pre-commit` admit a staged package marker while the obligation reports. Done when
      `tests/unit/adapters/repo/hook/test_staged_text.py` passes with both states.
- [x] 1.4 Declare `identifier-source`, which this batch ships for the first time, as reporting.
      Done when `tests/unit/repository/test_paradigm_names.py` expects a source gap among the
      reported gaps and the names it excuses nothing for among the required ones.

## 2. Documents

- [x] 2.1 Add the Changed line to the Unreleased section of `CHANGELOG.md`. Done when Prettier,
      Vale and codespell accept it.

## 3. Lane

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.

## Workflow follow-up

- The two governed repositories that the obligation blocked bind the release that carries this
  Change in their own lanes.
- The owner's ruling on the obligation's scope, and the Change that arms it with a repair and a
  reach preview, follow the committee's resolution.
