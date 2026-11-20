# Tasks

## 1. The gates

- [x] 1.1 Add the three cases: a clean selection lists the repository equally often at two sizes
      in both gates; under an ignore file it costs the same native runs at two sizes; under an
      ignore file a drifting file is reported and an excluded file is left. Done when the first
      two fail without 1.2 and 1.3.
      (Before the change, in a scratch copy of the landed head: the listing case fails, (6, 28)
      against (14, 44) listings for two and six files, and the ignore-file case fails. The three
      cases are in `ead858920`.)
- [x] 1.2 Pass one listing of the repository to the lookups of the format gate, and let
      `markdown-lint` take its format verdict from the bulk path. Done when the first case
      passes and the tests of both gates pass.
      (At `ead858920` the listing case passes; the tests of both gates and of their callers and
      importers pass in the lane, 81, 120 and 108 cases.)
- [x] 1.3 Ask Prettier which named files the ignore file excludes in one process. Done when the
      second and third cases pass and the JavaScript lint passes on the new script.
      (At `ead858920` the two ignore-file cases pass and the JavaScript lint passes with
      `prettier-ignored.mjs`.)

## 2. Acceptance

- [ ] 2.1 Measure the three gates on ETHOS's tree and on one governed checkout before and after,
      in one load window. Done when every verdict is unchanged and the counts of commands are
      in the design's order.
- [x] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head and the hosted runs of that head pass on both forges.
      (At `7bd573ad9` on 2026-11-20 the pre-check passes with no finding and readiness passes with
      its 28 gates. The pre-check ran its full selection at `a9e90ab6f`, 413 test modules, 8,337
      passed and 3 skipped, and from there the selection of the one test file that differs, 43
      modules, 371 passed and 1 skipped.
      GitHub's push run 44655144202 and GitLab's pipeline 16815 of `7bd573ad9` pass. The run's
      link observation, which may fail, counted three redirects; `64c12fc64` names those
      sources at their new addresses.)
