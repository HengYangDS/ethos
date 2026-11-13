# Tasks

## 1. One worktree list owner

- [x] 1.1 Add `src/ethos/adapters/repo/worktree_list.py` with `parse_worktree_list`,
      `listed_worktrees` and `raw_worktree_records`, which moves there from `worktree_effects.py`.
      Done when the parser and refusal cases of `tests/unit/adapters/repo/test_worktree_list.py`
      pass and `tests/unit/mutation/test_worktree_effects_failure_matrix.py` passes with its
      NUL-form listing. Evidence: red at 10:59:13, before the implementation:
      `test_worktree_list.py` failed to import its module and
      `test_worktree_record_rejects_duplicate_path_records` failed on its NUL-form listing. Green at
      11:16:50 in `fb8121ca9`: 1,181 passed and 1 Windows-only test skipped over 58 test files.
- [x] 1.2 Move every other reader of `git worktree list` to the owner, keeping what a failed listing
      meant to it. Done when `worktree_list.py` holds the only `git worktree list` invocation under
      `src/`, `tools/ci/delivery/acceptance/brownfield.py` parses its listing with
      `parse_worktree_list`, and the unit tests of every migrated module pass. Evidence: in
      `fb8121ca9`, `worktree_list.py:44` is the only `git worktree list` invocation under `src/`,
      `brownfield.py:203` parses its listing with `parse_worktree_list`, and the 58 test files that
      reach the migrated modules passed at 11:16:50.
- [x] 1.3 Report `prunable` and `prune_reason` for each worktree in lane status and declare both in
      `system/schemas/kernel/workspace-status.schema.json`. Done when
      `test_lane_status_reports_each_worktree_as_git_lists_it` fails before the change and passes
      after it, and `tests/unit/lanes/status/test_projection.py` passes. Evidence:
      `test_lane_status_reports_each_worktree_as_git_lists_it` failed at 10:59:13 with its module
      and passed at 11:16:50 in `fb8121ca9`, with `tests/unit/lanes/status/test_projection.py`.
- [x] 1.4 Add the Fixed and Added lines to the Unreleased section of `CHANGELOG.md`. Done when
      Prettier and Vale accept them. Evidence: Prettier and Vale accepted `CHANGELOG.md` when
      `fb8121ca9` was committed at 11:17:50.

## 2. Acceptance

- [x] 2.1 Pass the architecture and static checks at the lane head. Done when
      `test_no_behavior_is_implemented_twice` and `test_no_function_grows_past_its_allowance` pass
      with the decision-density baseline unchanged, and Ruff, ty, import-linter, the module-layout
      check, the per-file code ceiling and the source budget pass. Evidence: at `cf71d0742` the
      delta precheck passed `tests/architecture`, `test_no_behavior_is_implemented_twice` and
      `test_no_function_grows_past_its_allowance` among it, at 12:39:09, with
      `tests/fixtures/decision-density-baseline.json` unchanged since `aa9f85d51`; the full precheck
      at `46417024d` passed Ruff, ty, import-linter and the per-file code ceiling; readiness passed
      28 gates with none failing, `module-layout` and `source-budget` among them, at 12:36:55.
- [x] 2.2 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head. Evidence: the full precheck at `46417024d` found, at 12:05:27, only the two supply-image
      binding tests, which pass since the binding in `0ff092e01` (37 of 37 at 12:29:22); the delta
      precheck from `46417024d` passed at `cf71d0742` with no finding at 12:39:09; readiness at
      `cf71d0742` passed 28 gates with none failing at 12:36:55.
