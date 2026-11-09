# Tasks

## 1. Behaviour

- [ ] 1.1 Report and delete an unread release key. Done when paradigm tests show `version_source`
      and `tag_pattern` reported as `release-binding`, also without release tags, and deleted by the
      repair in the same pass that keeps `mirror`; a `[release]` left empty removed with its
      comments; and a multi-line value beside the mirror left reported. `_RELEASE` in
      `test_paradigm_repair.py` and the release fixture of
      `tests/unit/cli/test_lane_paradigm_repair.py` drop the two keys; the accepted-mirror
      `release-table` case keeps them and asserts that the same pass deletes them.

## 2. Acceptance

- [ ] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
