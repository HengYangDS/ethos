# Tasks

## 1. The place of a wait that ends

- [x] 1.1 Add `test_a_wait_that_ends_unadmitted_gives_up_its_place` with one case each for the
      bound, an OS error while waiting and an interrupt. Done when each case fails at the base
      because the queue still lists the run's ticket. Evidence: lane commit `877faafcc`; in the
      preparation clone on the base's product code the three cases failed on the run's ticket still
      in the queue.
- [x] 1.2 Register the release of the place in `admitted_host_work` as soon as the place exists, so
      that it covers the wait and the admitted body. Done when the three cases pass,
      `test_a_bounded_wait_names_the_holder` again requires that only the holder's record remains,
      and the function's decision density is unchanged. Evidence: lane commit `877faafcc`; the
      admission and host proof modules passed in the lane with three more, 102 tests, at `7c625c6a7`
      (01:12:28).
- [x] 1.3 Add `test_a_place_that_cannot_be_given_up_never_replaces_the_exit_in_flight` with one case
      for each wait ending and one for a normal end, and give the place up through an exit callback
      that keeps an exit in flight, notes the failed release on it and names
      `host_admission_unavailable` when there is none. Done when the four cases pass, having failed
      with a plain callback and again without the note, the queue is empty after the real release,
      and `admitted_host_work` keeps its decision density. Evidence: lane commits `b9a161a24` and
      `8215dbacb`. The four cases failed with a plain callback in the preparation clone, and three
      failed again without the note in the lane (3 failed, 29 passed). With it the decision density
      guard and four host modules passed 103 tests at 02:10:46.

## 2. The result of a refused host proof

- [x] 2.1 Extend `test_a_contended_host_proof_blocks_with_no_path_of_the_holder` to require the
      readiness results, `data.executed`, `data.not_run` and the one admission gap, and add
      `test_a_host_proof_without_a_usable_host_root_keeps_its_readiness_results` with one case each
      for a relative data home and an unwritable queue, both set through `XDG_DATA_HOME`. Done when
      the three fail at the base on an empty `data.checks`. Evidence: lane commits `877faafcc` and
      `b9a161a24`; in the preparation clone on the base's product code the three failed on an empty
      `data.checks`, also through the environment seam.
- [x] 2.2 Raise a refused admission from `_admitted_gates` with the readiness results and the names
      of the other gates, and report both in the host result. Done when the three tests pass and
      `observe_gate_execution` keeps its pinned decision density. Evidence: lane commit `877faafcc`;
      the host proof module passed in the two lane runs that tasks 1.2 and 1.3 name.
- [x] 2.3 Record both repairs under Unreleased, Fixed in `CHANGELOG.md`. Done when Prettier accepts
      the file. Evidence: lane commits `877faafcc` and `b9a161a24`; Prettier accepted the file at
      each commit.

## 3. Lane and hosted acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: at `da63d1e11` the static precheck passed with no finding at 02:24:07, and
      readiness passed 28 gates with none failing at 03:26:10.
- [x] 3.2 Pass the hosted runs of that head. Done when the run of each forge passes. Evidence:
      GitHub run 43746618955 and GitLab pipeline 15865 of `da63d1e11` passed every job, read at
      03:04:38.
