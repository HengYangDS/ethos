# Tasks

## 1. Readiness run

- [x] 1.1 Specify the readiness run with failing tests. Done when tests fail for a run that executes
      only the readiness tier, reports the test and package gates as not run, records no
      attestation, and fails when one readiness gate fails. The tests failed first on the missing
      `readiness_observation`.
- [x] 1.2 Add `--readiness` to `ethos prove`. Done when those tests and the existing proof CLI tests
      pass. 193 gate and proof CLI tests pass, Ty reports nothing, and a narrowed or dry-run
      readiness request refuses `proof_readiness_options_invalid`.
