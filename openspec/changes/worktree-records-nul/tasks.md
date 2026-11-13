# Tasks

## 1. One worktree list owner

- [ ] 1.1 Add `src/ethos/adapters/repo/worktree_list.py` with `parse_worktree_list`,
      `listed_worktrees` and `raw_worktree_records`, which moves there from `worktree_effects.py`.
      Done when the parser and refusal cases of `tests/unit/adapters/repo/test_worktree_list.py`
      pass and `tests/unit/mutation/test_worktree_effects_failure_matrix.py` passes with its
      NUL-form listing.
- [ ] 1.2 Move every other reader of `git worktree list` to the owner, keeping what a failed listing
      meant to it. Done when `worktree_list.py` holds the only `git worktree list` invocation under
      `src/`, `tools/ci/delivery/acceptance/brownfield.py` parses its listing with
      `parse_worktree_list`, and the unit tests of every migrated module pass.
- [ ] 1.3 Report `prunable` and `prune_reason` for each worktree in lane status and declare both in
      `system/schemas/kernel/workspace-status.schema.json`. Done when
      `test_lane_status_reports_each_worktree_as_git_lists_it` fails before the change and passes
      after it, and `tests/unit/lanes/status/test_projection.py` passes.
- [ ] 1.4 Add the Fixed and Added lines to the Unreleased section of `CHANGELOG.md`. Done when
      Prettier and Vale accept them.

## 2. Acceptance

- [ ] 2.1 Pass the architecture and static checks at the lane head. Done when
      `test_no_behavior_is_implemented_twice` and `test_no_function_grows_past_its_allowance` pass
      with the decision-density baseline unchanged, and Ruff, ty, import-linter, the module-layout
      check, the per-file code ceiling and the source budget pass.
- [ ] 2.2 Pass readiness and the precheck at the lane head. Done when each passes on the committed
      head.
