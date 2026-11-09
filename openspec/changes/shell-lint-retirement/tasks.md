# Tasks

## 1. Retirement

- [x] 1.1 Remove ETHOS's `shell-lint` gate, session and hook with every reference. Done when
      `git grep -nE 'shell_lint|shell-lint'` outside the archive finds only this Change and its
      changelog bullet, the paradigm's ShellCheck carrier remains, and the registry loads. At
      `91af54fd0`, `git grep -nE 'shell_lint|shell-lint'` outside the archive finds only this Change
      and its changelog bullet, the paradigm's ShellCheck carrier
      `.config/checks/shellcheck/.shellcheckrc` remains, and the registry loads: readiness ran 28
      gates there.
- [x] 1.2 Point the shipped shell ownership and format rows at the paradigm's script refusal. Done
      when the format-selection tests pass with the new rows. The shell `[[ownership]]` and
      `[[format]]` rows name `repository-paradigm`, `ethos prove --json` and recorded generator
      output. `test_format_selection.py` passed among 189 focused tests from 07:35:47 to 07:35:58,
      and again in the impacted sweep at `5e473321d`.
- [x] 1.3 Test the session inventory helper directly. Done when the new test fails on a helper that
      keeps deleted paths and passes on the current one.
      `test_session_paths_keep_live_files_and_drop_deleted_ones` failed against a helper that kept
      deleted paths at 07:36:34, and passed against the current `tracked_files` at 07:36:36.
- [x] 1.4 Record the removal in `CHANGELOG.md` `[Unreleased]`. Done when a `### Removed` bullet
      names the gate and the descriptive rows. `CHANGELOG.md` `[Unreleased]` `### Removed` names the
      gate, its session and hook, the kept carrier and the descriptive rows, at `91af54fd0`.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. At `5e473321d` the impacted sweep of 52 test files passed 757 tests from
      07:45:41 to 07:47:19. At `91af54fd0` readiness passed 28 gates from 07:50:11 to 07:51:16, and
      the precheck passed every check but its own 100-column heuristic, on the quality Skill's
      single-line YAML front-matter description, which the repository's Markdown gates accept.
