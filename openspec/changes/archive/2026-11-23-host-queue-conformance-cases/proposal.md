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
- The test fixtures' Git helper (`tests/support/governed_repository.py`, `git`) and the two
  children of the signer fixture (`tests/support/fixture_signer.py`) run through the product's
  process owner, with a bound of 120 seconds for Git. The owner captures in files where a
  pipe's reader would wait, and closes the child's standard input. On the
  proposal ref's first Windows run the session ended in the ten-minute limit of one case of
  `test_proof_slot.py` on three of four hosts, each time in this helper, while its reader
  threads waited for the end of a pipe; on the fourth host all 130 cases passed. The process
  owner has captured in files on Windows since 0.2.0-alpha.26 for the same wait; the helper had
  kept its pipes.
- Three cases of the four modules read the host they run on, and would fail on a hosted leg. They
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

`tools/ci/delivery/pipeline.py`, the list of cases; `tests/support/governed_repository.py` and
`tests/support/fixture_signer.py`, the Git helper and the signer that most tests of the suite
use; `tests/unit/gates/test_host_admission.py`
and `tests/unit/gates/test_proof_slot.py`, three cases and three assertions;
`tests/unit/cli/test_host_run.py`, one assertion. Every host conformance leg runs 110 more
cases: 17 seconds on this macOS arm64 host, one module a run; the hosted platforms are measured
by this Change's own runs. Nothing that a governed repository reads.
