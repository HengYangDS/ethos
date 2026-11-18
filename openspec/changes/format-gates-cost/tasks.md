# Tasks

## 1. The gates

- [ ] 1.1 Add the three cases: a clean selection lists the repository equally often at two sizes
      in both gates; under an ignore file it costs the same native runs at two sizes; under an
      ignore file a drifting file is reported and an excluded file is left. Done when the first
      two fail without 1.2 and 1.3.
- [ ] 1.2 Pass one listing of the repository to the lookups of the format gate, and let
      `markdown-lint` take its format verdict from the bulk path. Done when the first case
      passes and the tests of both gates pass.
- [ ] 1.3 Ask Prettier which named files the ignore file excludes in one process. Done when the
      second and third cases pass and the JavaScript lint passes on the new script.

## 2. Acceptance

- [ ] 2.1 Measure the three gates on ETHOS's tree and on one governed checkout before and after,
      in one load window. Done when every verdict is unchanged and the counts of commands are
      in the design's order.
- [ ] 2.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head and the hosted runs of that head pass on both forges.
