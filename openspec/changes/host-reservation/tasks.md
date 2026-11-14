# Tasks

## 1. The record, the projection and the cap

- [x] 1.1 `HostQueue.enter` records the operation and the owner mark beside its three old fields,
      and one projection carries the operation, executable, owner mark, pid, start time and
      `same_repository` with no path. Done when the admission tests pass, including the case where
      an older three-field record projects an empty operation and owner.
- [x] 1.2 The contention gap and the waiting event use that projection. Done when the gap is
      `host_admission_contended:<operation>:<pid>:<since>`, names the executable for a record
      without an operation, and the result holds no holder's path.
- [x] 1.3 `HostPlace.environment` keeps a smaller positive caller worker count. Done when a caller's
      4 survives under a cap of 8 and a larger or non-numeric value does not.

## 2. The read

- [x] 2.1 `HostQueue.entries` lists every live recorded ticket in arrival order as `holding` or
      `waiting` without removing a file. Done when a dead holder is absent and its record survives
      until the next waiter.
- [x] 2.2 `host status` is a catalog command with the operation `host.status`, effects `read` and
      exit `observe`, implemented by `inspect_host_queue`. Done when the operation catalog test
      counts 105 operations and the argv table selects `host.status` for
      `host status --guest-cpus 8`.
- [x] 2.3 `--guest-cpus N` reports `reservation` and answers `host_reservation_exceeded` or
      `host_reservation_invalid`. Done when the three cases pass in `test_host_run.py`.
- [x] 2.4 A host root or declaration that cannot be read answers `block` with its gap. Done when
      `inspect_host_queue` returns the declaration's or the root's named gap.

## 3. The host proof

- [x] 3.1 `observe_gate_execution` runs the readiness tier without waiting and the rest under
      `admitted_host_work`, with the environment exported and `data.admission` recorded. Done when
      the host proof tests hold one `proof.host` ticket, take none for a readiness-only plan, and
      join a live admission.
- [x] 3.2 A bounded wait runs no test or package gate, answers `block` with the contended gap and
      exits 1; an unwritable root answers `host_admission_unavailable`. Done when both cases pass.

## 4. Documents

- [x] 4.1 The guide `docs/guides/ci-guest-host.md`, its index line, the reference's host section,
      the changelog and the spec deltas. Done when Prettier, codespell, Vale and
      `openspec validate host-reservation --strict` pass.

## 5. Lane only

- [ ] 5.1 Run the precheck and readiness at the lane head, then the full proof. Done when each
      passes on the committed head.
- [ ] 5.2 Prove the acceptance on the workstation: one foreground host proof holds `proof.host`, a
      second reads it with `ethos host status --json`, and a third waits and names it. Done when
      the three observations match.
- [ ] 5.3 Prove mixed engines: a repository on an older release queues behind the new holder and
      the reverse. Done when both directions are observed.
- [ ] 5.4 Measure the guests' vCPU sum, run `ethos host status --guest-cpus N`, and raise
      `reserved_cpus` if it does not fit. Done when the read passes on the reference host.
- [ ] 5.5 Declare the hosted job's worker count as 4 in the pipeline model and both projections.
      Done when `.config/ci/pipeline.cue` and both generated pipelines name 4 workers for the heavy
      test steps.

## Workflow follow-up

- Delivery: on the first hosted runs on both forges that carry this Change, observe on every
  platform that the job takes and frees its ticket and that the worker count stays 4.
