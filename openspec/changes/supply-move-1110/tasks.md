# Tasks

## 1. Supply move

- [ ] 1.1 Move every lock and pin under the cutoff. Done when `uv lock --upgrade` with the cutoff
      changes neither `uv.lock`, the npm lock holds the newest stable transitive versions, and the
      action pins name the newest stable releases' commits.
- [ ] 1.2 Rebuild and bind the CI supply image. Done when the bound digest is in
      `.config/ci/pipeline.cue` and the CI projection check passes.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests and readiness at the committed head. Done when each passes there.
