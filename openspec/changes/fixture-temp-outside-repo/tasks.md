# Tasks

## 1. Refuse a temporary root inside a repository

- [x] 1.1 Add the refusal and call it at session start. Done when a base directory inside a Git work
      tree or Git directory is refused, one outside any repository passes, and the test fails before
      the refusal exists. RED: with a stub the test failed (`None` for a directory inside a
      repository); GREEN in e46958af3 and 99d4822d9: a base directory inside a work tree or `.git`
      refuses, one outside passes, a missing `git` refuses; a probe session with `--basetemp` inside
      a repository exited before any test.

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head. At b72198e5f: the precheck passed with 0 findings, the impacted
      tests (37 files) passed 292 with 1 skipped, and readiness passed 28 of 28 gates; the full
      suite runs in the proof.
