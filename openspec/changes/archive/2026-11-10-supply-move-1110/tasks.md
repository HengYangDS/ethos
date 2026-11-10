# Tasks

## 1. Supply move

- [x] 1.1 Move every lock and pin under the cutoff. Done when `uv lock --upgrade` with the cutoff
      changes neither `uv.lock`, the npm lock holds the newest stable transitive versions, and the
      action pins name the newest stable releases' commits. Evidence: against the cutoff
      2026-11-09T04:45:00Z, `uv lock --upgrade --exclude-newer` changed neither `uv.lock` (121
      packages) nor the quality-sample lock (11 packages); `npm update --package-lock-only --before`
      moved the five transitive packages while every direct pin was already newest; 79d0bd596 pins
      docker/login-action v4.8.0 at 8aa5831fb8d48d8f76594c7ddde61ae58019f550, and the other six
      action pins and every Mise tool are the newest eligible releases.
- [x] 1.2 Rebuild and bind the CI supply image. Done when the bound digest is in
      `.config/ci/pipeline.cue` and the CI projection check passes. Evidence: run 42759381555 built
      and published sha256:1380c370d47355b1fe98e45d6df71e76489541adb6d5a09abb9ed960a6d7058b from
      79d0bd596; deb761f85 binds it, the projection check reads conforming, and the supply image
      currency and provider projection tests passed (37 passed, 13:08:42 to 13:08:51).

## 2. Acceptance

- [x] 2.1 Pass the impacted tests and readiness at the committed head. Done when each passes there.
      Evidence: the 33 impacted test targets passed at 79d0bd596 except the two that need the new
      binding (862 passed, 2 failed, 1 skipped, 13:01:47 to 13:06:46), and those passed after it (37
      passed, 13:08:42 to 13:08:51); readiness passed 28 gates at deb761f85 (13:09:08 to 13:10:26).
