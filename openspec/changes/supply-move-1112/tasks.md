# Tasks

## 1. Supply move

- [ ] 1.1 Move every pin and lock under the cutoff, except Mise. Done when the Mise tools name the
      newest eligible releases, `uv lock --upgrade` with the cutoff changes nothing more, the npm
      lock holds the newest stable transitive versions before the cutoff, and Mise and its CI
      bootstrap stay at 2026.10.25.
- [ ] 1.2 Rebuild and bind the CI supply image. Done when the bound digest is in
      `.config/ci/pipeline.cue` and the CI projection check passes.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests and readiness at the committed head. Done when each passes there.
