# Tasks

## 1. The entries enter the repository

- [x] 1.1 Add `defects/` at the repository root with the 73 entry files and no other file. Done when
      `git ls-files defects` lists 73 entry files and a script that applies the design's reading
      rules reports no malformed entry and no `since` or `fixed_in` tag that does not resolve.
      Evidence: the entries landed on `dev` at `39a1a8ffc`. Read there on 2026-11-26 at 05:09,
      `git ls-files defects` lists 73 files, and a script of the reading rules reads 73 entries,
      65 open and 8 closed, none malformed. Every `since` that is set names a released tag, one
      is empty, which the rules admit, and no `fixed_in` is set. The release lane of
      0.2.0-beta.12 then names that release's tag in nine fields.
- [x] 1.2 Add `defects/**/*.md` to the `globs` of
      `.config/checks/markdownlint-cli2/.markdownlint-cli2.yaml`, and the scope
      `text.frontmatter.workaround` to the `IgnoredScopes` of `.config/checks/vale/vale.ini`. Done
      when a direct `markdownlint-cli2` run reports no issue in `defects/`, Vale with the
      repository's configuration reports nothing there, and the tests that hold a title's
      diagnostics and a TOML entry's unread workaround pass. Evidence: on `dev` at `39a1a8ffc`,
      2026-11-26 at 05:10, a direct `markdownlint-cli2` run with the repository's configuration
      reported 0 issues over the 1,759 files of its globs, `defects/` among them, and Vale
      reported 0 errors, 0 warnings and 0 suggestions in the 73 files.
      The test `test_common_vale_policy_reads_a_toml_title_and_never_an_entry_workaround` holds
      both; its module passed 10 tests at the release lane's head `dacdb7bd4` at 05:23.

## 2. The gates before the proof

- [x] 2.1 Run `ethos lane format --check` on the lane. Done when it reports no refusal and a second
      run over the same files reports the same result. Evidence: at the release lane's head
      `dacdb7bd4`, 2026-11-26 at 05:21, two runs each passed over 1,421 files with no refusal.
- [x] 2.2 Run `ethos prove --gate` for `markdown-lint`, `prose`, `markdown-links` and
      `source-format`. Done when each gate passes on the committed head. Evidence: the four gates
      ran inside the readiness run of the release lane at the committed head `dacdb7bd4`, and
      each passed (2026-11-26, 05:20:46). This Change's own lane passed its full proof at
      `39a1a8ffc` on 2026-11-25.
- [x] 2.3 Run `ethos lane redact private-addresses --json`. Done when the preview names nothing
      under `defects/` and it read a feed from a declared peer's remote. Evidence: at
      `dacdb7bd4`, 2026-11-26 at 05:21, the preview passed in the state `previewed`, which the
      command reaches only with a known feed, and it named 0 occurrences in the whole tree.
