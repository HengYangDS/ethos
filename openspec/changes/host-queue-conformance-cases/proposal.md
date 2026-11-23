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

- The host conformance cases gain the three test modules of the host queue:
  `tests/unit/gates/test_host_queue_entry.py`, `test_host_place_lifetime.py` and
  `test_host_admission.py`. Together they hold 66 cases.
- `tests/unit/gates/test_proof_slot.py`, the proof's own admission, was listed first and is left
  out: on the proposal ref's Windows legs it ended in a ten-minute timeout on three of four hosts,
  each time while a `git` child of a test fixture never returned, at two different cases; on the
  fourth host it passed. The cause is not found. The module still runs in the suite; its Windows run
  is a follow-up.
- Three cases of those modules read the host they run on, and would fail on a hosted leg. They
  are made independent of it: the load reading that Windows lacks is patched without requiring
  the name; the two cases of the worker cap pin the CPU count instead of reading the runner's;
  the waiting event's holder state is expected as the platform gives it.
- Four assertions that a result names no repository path compared the path's plain text with
  JSON text, where a Windows path's backslashes are doubled, so they could not fail on Windows.
  They compare the path as JSON writes it. Three are in those modules and one is in
  `tests/unit/cli/test_host_run.py`.
- No product code changes and no test is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement "Hosted host conformance runs in declared tiers" names the tiers and their
platforms, not the cases, so `skip_specs: true` applies.

## Impact

`tools/ci/delivery/pipeline.py`, the list of cases; `tests/unit/gates/test_host_admission.py`
and `tests/unit/gates/test_proof_slot.py`, three cases and three assertions;
`tests/unit/cli/test_host_run.py`, one assertion. Every host conformance leg runs 66 more
cases: 10 seconds on this macOS arm64 host, one module a run; the hosted platforms are measured
by this Change's own runs. Nothing that a governed repository reads.
