# Tasks

## 1. The case list

- [x] 1.1 Add the four test modules of the host queue and of the proof's admission to the host
      conformance cases. Done when the unit tests of the case list pass and the session's command
      names the four files. (At `06371e97b` the list names the four files;
      `tests/unit/ci/delivery/test_pipeline.py` passes, 7 cases, and its two tests derive from the
      list. The hosted session ran 130 cases where it ran 20: on Linux 126 passed and 4 skipped,
      against 16 and 4 at `3e94151ea`.)
- [x] 1.2 Make the cases that read the runner independent of it. Done when the modules pass on this
      host, and under a probe that shows them three CPUs and no load reading every case passes but
      the one whose expectation is read from the host when the module is imported. (At `4dcf4e885`
      the four modules pass here, 110 cases. Under the probe 5 failed before the repair and 1 after
      it, the one named in the condition. The hosted macOS leg, three CPUs, passed at `da4227508`:
      126 passed, 4 skipped.)
- [x] 1.3 Run the fixtures' Git helper and the signer fixture's children through the process owner,
      with a bound. Done when the modules that call them pass in the whole pre-check, and a failed
      command raises as before. (At `06371e97b` the pre-check passed with 0 findings: 47 impacted
      test files, 476 passed, 1 skipped; a change of test support selects no more, so the other
      callers are the hosted quality gates' whole suite, which passed in run 45271550142.
      `tests/architecture/test_test_fixture_boundaries.py` still expects `CalledProcessError` from
      the helper and passes, 8 cases.)
- [x] 1.4 Run the cases on every hosted platform. Done when the proposal ref's push run and one
      typed dispatch with the Windows legs have ended, each leg's result for the listed modules is
      read by name, and each leg's added time is written here. (Runs 45271550142 and 45271584929 at
      `06371e97b`, read from each leg's log; the logs print counts, not names, and 130 is the 20
      earlier cases plus the 110 of the four modules. Linux x64 with Python 3.12, 3.13 and 3.14: 126
      passed, 4 skipped in 6.1, 7.0 and 7.1 seconds, against 3.2 before on 3.12. Windows x64 with
      3.12, 3.13 and 3.14: 119 passed, 11 skipped in 30.5, 26.0 and 31.1 seconds, against 4.8, 4.6
      and 4.6. Windows arm64: 119 passed, 11 skipped in 41.1 seconds, against 5.5. macOS arm64 was
      cancelled by the forge for capacity in both runs; at `da4227508`, before the helper changed,
      it took 13.3 seconds against 3.2. Two earlier dispatches ended in the test's ten-minute limit
      on three and then two of the four Windows hosts; design decision 6 records them.)
