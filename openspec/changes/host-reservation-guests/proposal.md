# Proposal

## Why

`host-reservation` gave a workstation one queue for heavy work, a reader of that queue and a
ticket that a foreground proof holds. This Change is the second half of the gate's row on the
host: DR-0026's item on the shared host, which the committee's resolution of 2026-11-14, recorded
by DR-0029, counts as done only with its second Change. The owner decided on 2026-11-15 that this
second half (a waiting proof keeps its place, guests inside the reservation, the owner mark on a
work directory) is required work of 0.2.0 in batch 0.2.0-beta.12: it is gate work and takes no
off-gate slot. Measured on the releasing host on 2026-11-14 and 2026-11-15:

- A proof that waits for its ticket at its test gates gives up after the admission timeout and
  requeues at the tail. Sessions wrap it in `ethos host run --wait` to keep its place. On
  2026-11-15 one holder kept the only slot for about 106 minutes while others waited; the
  admission bound declared there is 3,600 seconds.
- The worker cap is the CPUs less the reservation whatever the number of slots, so a second slot
  cannot open.
- One slot cannot tell a one-core hour from an eighteen-core minute: a one-core build held the
  slot for about 20 minutes while seven tickets waited.
- The rule of at most two tickets for one session is kept by each session's script. One session
  held four for two minutes, because several waiters passed the same check.
- Three of four live tickets declared no operation and no owner; only an engine of this release
  line writes them.
- `ethos host status --guest-cpus 20` on a host of 18 CPUs whose three guests hold 20 virtual CPUs
  reports `host_reservation_exceeded` with a next action that no value satisfies.
  `host-reservation` withdrew its task on this under DR-0016.
- An interrupted proof released its ticket while two of its gate process groups ran on, and its
  scratch of 5.9 GB stayed under the temporary root.
- One governed product's session found 5 of 16 problems only after a ticket had run on inputs they
  invalidate, and now admits heavy work on a receipt that binds each input by digest.

## What Changes

- A waiting run keeps its place behind tickets whose holders live: `ethos host run`, a host proof
  and a full proof no longer end their wait for the host queue at `timeout.admission_seconds`.
  Every wait still ends, at the caller's own `--wait` and at the latest at the admission ceiling,
  the parameter's declared maximum of 36,000 seconds.
- `timeout.admission_seconds` still bounds a full proof's wait for its repository's slot and for
  calm load, without the time it spent behind a live holder of the host slot.
- The worker cap is one slot's share of the CPUs that the reservation leaves.
- The guests' read names a repair that can be followed: the value of `reserved_cpus` that holds
  the guests, or the guests' sizes where no value does. It reports the most this host can reserve.
- `ethos host run --work <name>` claims `build/runtime/work/<name>/` for the run's owner with a
  mark inside it. A directory that carries another owner's mark refuses the run before it queues.
- The scratch root that the Python behavior probe makes carries the same mark when its proof
  holds or has joined a host ticket.
- Designed here and built later, each with its size and release in the design: the cap of tickets
  for one holder and a rank among them, a declared CPU share, a release that ends its work, and a
  readiness receipt. Tickets of earlier engines that declare no owner stay as they are.
- Every holder gives its place up the way `host-ticket-release` made the waiting run do: an
  OS error while leaving never escapes raw and never skips a later release. Read and not
  run: the full proof leaves its place in a `finally` ahead of the repository's slot, and
  the queue keeps a ticket's lock when its record cannot be removed.
- A run that joined an outer ticket states that ticket and the outer run states its wait.
  Measured on 2026-11-15: a proof that waited about 65 minutes under `ethos host run`
  reported a wait of 0, so the weekly page's host minutes have no reader for the wait.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: MODIFIED `Heavy local work is admitted host-wide`,
  `The host declaration bounds admitted work`,
  `Full proofs and nested work share the host admission` and
  `The guests' CPUs are checked against the reservation`; ADDED
  `A run's work directory carries its owner's mark` and
  `A ticket holder's test scratch carries its owner's mark`.

## Impact

`src/ethos/adapters/gates/host_admission.py`, `proof_slot.py`, `python_quality.py` and the new
`host_work.py`; `src/ethos/application/host.py` and `application/proof/host.py`;
`src/ethos/repository/paradigm/parameters.py`; `src/ethos/contracts/operations/host.py` and three
rows of `src/ethos/contracts/codes/gaps.toml`; their tests; `docs/reference/command-plane.md`,
`docs/reference/configuration.md`, `docs/guides/ci-guest-host.md` and `CHANGELOG.md`.

The host declaration file, a ticket's file name and its record's fields do not change, so engines
of earlier releases keep sharing the queue. They keep their own bound and their own worker cap.
A wait for the host queue no longer ends at `timeout.admission_seconds`, which the Unreleased
entry marks as breaking, and the worker cap falls on a host that declares more than one slot.

Measured in line-equivalents of the source budget against the base: about 103 of product code and
352 of tests, shared test support included. The test ceiling had 247 free at the base, so the
batch's budget step lands first.
