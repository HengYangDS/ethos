# Tasks

## 1. One received selection

- [ ] 1.1 Subtract the paths that Git attributes mark vendored or generated in
      `authored_source_files`, and drop the second subtraction in `authored_text_files`. Done when
      `test_received_paths_leave_every_authored_selection` fails before the change and passes after
      it, and the tests under `tests/unit/adapters/gates/` pass with the prose fixture standing in
      for the join's attribute read.
- [ ] 1.2 Add the Fixed line to the Unreleased section of `CHANGELOG.md`. Done when Prettier and
      Vale accept it.

## 2. Acceptance

- [ ] 2.1 Pass the static precheck and readiness at the lane head. Done when each passes on the
      committed head.
