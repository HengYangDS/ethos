# Tasks

## 1. Merge

- [x] 1.1 Merge the accepted candidate. Done when the merge commit keeps the CHANGELOG entries and
      the governance requirements of both sides, and Prettier and strict OpenSpec validation pass.
      Evidence: the native merge committed 6e2eeaa6d at 03:59:50 and kept the index-target CHANGELOG
      entry before the two peer identity entries and the index-target requirement before the four
      peer identity requirements; Prettier passed on both files, and the static precheck, which
      validates every Change strictly, passed at 6e2eeaa6d (04:00:22).

## 2. Acceptance

- [x] 2.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: the static precheck passed at 6e2eeaa6d (04:00:22); the tests where the two
      sides meet, the lane redaction, index prewrite, push check and marker verifier modules, passed
      (65 tests at 6e2eeaa6d, 04:00:23 to 04:01:29); and readiness passed 28 gates at 6e2eeaa6d
      (04:04:33), with the 6 heavy gates left to the proof.
