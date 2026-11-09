# Tasks

## 1. Gate

- [x] 1.1 Validate the publication ranges in the proof. Done when provider tests show a commit that
      the candidate's verifier refuses failing the gate, a clean range passing with peers that share
      a tip judged once, an empty range passing, an unobserved branch reported as a note, every
      configured peer unobserved refused as `commit_ranges_unobserved`, an invalid declaration
      refused with its gap, a checkout without a peer remote passing as not applicable, and the gate
      declared in the registry, planned by the full proof and bound to `src/ethos/`. In the impacted
      sweep at `9b2d96124` (23:07:13 to 23:08:57), the eight cases of `test_commit_ranges.py`
      passed, among them the registry case that plans the gate in the full set bound to
      `src/ethos/adapters/gates/commit_ranges.py`.
- [x] 1.2 Regenerate the CI projections if the registry is one of their inputs. Done when the
      `ci-projection` gate passes. The registry is an input of the CI projection policy;
      `ethos lane project --check` reported `conforming` at `9b2d96124` (23:09:34) without a
      regeneration, and readiness passed 29 gates, `commit-ranges` and `ci-projection` among them,
      from 23:31:39 to 23:33:27 at `5e2c9f834`.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head, and run
      `commit-ranges` there as host evidence. Done when each passes and the host report shows
      `applicable: true` with a judged target for each configured peer. The batch precheck passed
      with 0 findings at 23:34:13 to 23:34:17 against `12a61d097`, at `5e2c9f834`. The impacted
      sweep of 58 test files at `9b2d96124` passed 898 tests from 23:07:13 to 23:08:57 and failed 2,
      the supply image currency pair, which passed 37 tests at `5e2c9f834` from 23:13:56 to 23:14:19
      once the image was bound. Then readiness passed 29 gates, `commit-ranges` and `ci-projection`
      among them, from 23:31:39 to 23:33:27 at `5e2c9f834`. The host run of `commit-ranges` at
      `3b75a5a03` (22:54:29 to 22:54:45) reported `applicable: true` with two judged ranges held by
      both peers: `dev` from `12a61d097`, 1 commit, and `main` from `0f788d4a6`, 25 commits, both
      passing in 2.05 s.
