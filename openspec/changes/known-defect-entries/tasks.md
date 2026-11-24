# Tasks

## 1. The entries enter the repository

- [ ] 1.1 Add `defects/` at the repository root with the 68 entry files and no other file. Done when
      `git ls-files defects` lists 68 entry files and a script that applies the design's reading
      rules reports no malformed entry and no `since` or `fixed_in` tag that does not resolve.
- [ ] 1.2 Add `defects/*.md` to the `globs` of
      `.config/checks/markdownlint-cli2/.markdownlint-cli2.yaml`, and the scope
      `text.frontmatter.workaround` to the `IgnoredScopes` of `.config/checks/vale/vale.ini`. Done
      when a direct `markdownlint-cli2` run reports no issue in `defects/`, Vale with the
      repository's configuration reports nothing there, and the test that holds a title's
      diagnostics passes.

## 2. The gates before the proof

- [ ] 2.1 Run `ethos lane format --check` on the lane. Done when it reports no refusal and a second
      run over the same files reports the same result.
- [ ] 2.2 Run `ethos prove --gate` for `markdown-lint`, `prose`, `markdown-links` and
      `source-format`. Done when each gate passes on the committed head.
- [ ] 2.3 Run `ethos lane redact private-addresses --json`. Done when the preview names nothing
      under `defects/` and it read a feed from a declared peer's remote.
