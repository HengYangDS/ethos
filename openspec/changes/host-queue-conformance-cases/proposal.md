# Proposal

## Why

A place in the host queue is an operating-system lock on a file: `flock` on POSIX and
`LockFileEx` on Windows. The Change `host-slot-outlives-holder` rewrote how a place is entered,
probed and released, with one branch for each platform. Its tests ran on macOS in the full proof
and on Linux in the hosted suites of Python 3.12, 3.13 and 3.14. No hosted job ran them on
Windows:

- host conformance runs five named cases, and none of them is of the queue;
- the Windows suite leg, an observation leg, stopped in `tests/architecture` after four failures
  at 64 tests, on the qualification run of `3e94151ea` (2026-11-24) and on the scheduled run of
  `main` at `eee24a887` (2026-11-21) alike, so it reached no unit test.

Host conformance holds the cases that only a real host proves, and its Windows legs are required
wherever they run: a batch-head qualification, the drift schedule and the typed dispatch.

## What Changes

- The host conformance cases gain the four test modules of the host queue and of the proof's
  admission: `tests/unit/gates/test_host_queue_entry.py`, `test_host_place_lifetime.py`,
  `test_host_admission.py` and `test_proof_slot.py`. Together they hold 110 cases.
- No product code changes and no test is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement "Hosted host conformance runs in declared tiers" names the tiers and their
platforms, not the cases, so `skip_specs: true` applies.

## Impact

`tools/ci/delivery/pipeline.py`, the list of cases. Every host conformance leg runs 110 more
cases: 17 seconds on this macOS arm64 host, one module a run; the hosted platforms are measured
by this Change's own runs. Nothing that a governed repository reads.
