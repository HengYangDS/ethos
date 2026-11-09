# Tasks

## 1. Supply move

- [x] 1.1 Move both `uv.lock` files to the newest releases published before the 24-hour cutoff. Done
      when `uv lock --check` passes for both and the fixture lock test passes. Under the cutoff
      2026-11-08T14:56:12Z the project lock moved 16 packages and the fixture lock ruff 0.17.4;
      `uv lock --check` passed for both at 23:31:10, and the 11 test files that use the quality
      fixture passed 189 tests (1 skipped) from 23:44:05 to 23:47:51, both at `5e2c9f834`.
- [x] 1.2 Move the npm pins and overrides and remove the `dompurify` override. Done when
      `package-lock.json` resolves under the cutoff, `npm ci` installs it and the dependency audit
      passes. `npm install --package-lock-only --before=2026-11-08T14:56:12Z` resolved the lock with
      dompurify 3.4.17 and no override, `npm ci` installed it in the lane, and the
      `dependency-vulnerabilities` gate passed at `5e2c9f834` from 23:33:54 to 23:34:02.
- [x] 1.3 Move the direct dependency floors to the locked releases. Done when every moved direct
      dependency's floor in `pyproject.toml` names its locked version and `uv lock --check` passes.
      The floors of cel-expr-python, Cyclopts, Pydantic (also the build requirement), ruff,
      hypothesis, import-linter and ty name their locked versions, and `uv lock --check` passed at
      23:31:10.
- [x] 1.4 Rebuild and bind the CI supply image. Done when the image's manifest matches the moved
      files and the bound digest is in `.config/ci/pipeline.cue`. Supply run 42641237816 built
      `sha256:0b2f67e9f4ee5ffc9a8c718251514e242a1377049ffa7eb87b085060035bd04a` from `9b2d96124`;
      `5e2c9f834` binds it, all 5 GitLab jobs select it, and the supply image currency tests passed
      there from 23:13:56 to 23:14:19.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The batch precheck passed with 0 findings at 23:34:13 to 23:34:17 against
      `12a61d097`, at `5e2c9f834`. The impacted sweep of 58 test files at `9b2d96124` passed 898
      tests from 23:07:13 to 23:08:57 and failed 2, the supply image currency pair, which passed 37
      tests at `5e2c9f834` from 23:13:56 to 23:14:19 once the image was bound. Then readiness passed
      29 gates, `commit-ranges` and `ci-projection` among them, from 23:31:39 to 23:33:27 at
      `5e2c9f834`.
