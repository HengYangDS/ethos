# Tasks

## 1. The rule and its gate

- [x] 1.1 Add the pure spacing pass with tests for each list shape. Done when a stray blank line, a
      blank line before an introduced block and a missing separator after a spread item are each
      found and repaired, and a second pass changes nothing. Evidence: f10df8694 adds
      `repository/paradigm/markdown_spacing.py` and `test_paradigm_markdown_spacing.py`: six broken
      shapes are found and repaired to a fixed point, and three conforming texts, a fenced example
      among them, keep their bytes (in the 28 focused tests that passed 22:56:41 to 22:56:49).
- [x] 1.2 Apply the pass in the Markdown postimage and in `pre-commit`. Done when the formatting
      gate refuses a violation that Prettier accepts, `ethos lane format --apply` repairs it, and a
      staged violation refuses with its path and line. Evidence: against the old wiring the new gate
      test and the staged stray-blank case failed (22:43:40 to 22:43:46); with f10df8694 the
      Prettier postimage applies the rule, the Markdown gate adds `markdown-list-spacing` after the
      native lint reports, and `pre-commit` refuses `pre_commit_markdown_spacing:<path>:<line>`; the
      focused tests passed (28, 22:56:41 to 22:56:49), and the 33 targets that touch formatting, the
      Markdown gate or pre-commit passed (657, 22:58:05 to 23:01:13).
- [x] 1.3 Repair ETHOS's two violations and add the Changed line. Done when the rule finds no
      violation in ETHOS's authored Markdown and Prettier and Vale accept the changed files.
      Evidence: f10df8694 joins the two blocks in `docs/reference/configuration.md` and names the
      rule's owner there; the in-lane module then found no violation in ETHOS's authored Markdown,
      and Prettier and Vale accepted the changed files in the commit's checks.

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the precheck passed against 9ebeae1c8 with 0 findings (23:45:28 to 23:45:48),
      and readiness passed 28 gates at 9ebeae1c8 with the 6 heavy gates left to the proof (23:45:48
      to 23:47:58).
