# Tasks

## 1. Supply move

- [ ] 1.1 Move both `uv.lock` files to the newest releases published before the 24-hour cutoff.
      Done when `uv lock --check` passes for both and the fixture lock test passes.
- [ ] 1.2 Move the npm pins and overrides and remove the `dompurify` override. Done when
      `package-lock.json` resolves under the cutoff, `npm ci` installs it and the dependency audit
      passes.
- [ ] 1.3 Move the direct dependency floors to the locked releases. Done when every moved direct
      dependency's floor in `pyproject.toml` names its locked version and `uv lock --check` passes.
- [ ] 1.4 Rebuild and bind the CI supply image. Done when the image's manifest matches the moved
      files and the bound digest is in `.config/ci/pipeline.cue`.

## 2. Acceptance

- [ ] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there.
