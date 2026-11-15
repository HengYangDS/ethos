# Tasks

## 1. The place of a wait that ends

- [ ] 1.1 Add `test_a_wait_that_ends_unadmitted_gives_up_its_place` with one case each for the
      bound, an OS error while waiting and an interrupt. Done when each case fails at the base
      because the queue still lists the run's ticket.
- [ ] 1.2 Register the release of the place in `admitted_host_work` as soon as the place exists, so
      that it covers the wait and the admitted body. Done when the three cases pass,
      `test_a_bounded_wait_names_the_holder` again requires that only the holder's record remains,
      and the function's decision density is unchanged.

## 2. The result of a refused host proof

- [ ] 2.1 Extend `test_a_contended_host_proof_blocks_with_no_path_of_the_holder` to require the
      readiness results, `data.executed`, `data.not_run` and the one admission gap, and add
      `test_a_host_proof_without_a_usable_host_root_keeps_its_readiness_results` with one case each
      for an absent host root and an unwritable queue. Done when the three fail at the base on an
      empty `data.checks`.
- [ ] 2.2 Raise a refused admission from `_admitted_gates` with the readiness results and the names
      of the other gates, and report both in the host result. Done when the three tests pass and
      `observe_gate_execution` keeps its pinned decision density.
- [ ] 2.3 Record both repairs under Unreleased, Fixed in `CHANGELOG.md`. Done when Prettier accepts
      the file.

## 3. Lane and hosted acceptance

- [ ] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
- [ ] 3.2 Pass the hosted runs of that head. Done when the run of each forge passes.
