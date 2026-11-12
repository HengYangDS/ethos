# Tasks

## 1. One plan for one destination

- [x] 1.1 Drop the caller's spelling of the root from the formation plan. Done when the test that
      previews through a linked parent and through the reported canonical path fails before the
      change and passes after it, the retarget test still refuses, and the greenfield and Python
      starter tests pass. Evidence: 616b909f3 drops `requested_root` from `source_inputs`.
      `test_greenfield_plan_names_the_destination_not_its_spelling` failed before the change with
      two digests (18:06:48 to 18:06:57) and passed after it with the retarget test (18:07:08 to
      18:07:17); the 16 targets that exercise formation and adoption passed (378 passed, 18:07:49 to
      18:10:36).
- [x] 1.2 Add the Fixed line to the Unreleased section of `CHANGELOG.md`. Done when Prettier and
      Vale accept it. Evidence: 616b909f3 adds the Fixed line; Prettier and Vale accepted it in the
      commit's checks.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against d1be14275 with 0 findings (18:30:03 to 18:30:08),
      and readiness passed 28 gates at d1be14275 with the 6 heavy gates left to the proof (18:30:20
      to 18:31:43).
