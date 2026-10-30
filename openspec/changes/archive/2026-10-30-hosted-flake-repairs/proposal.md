# Proposal

## Why

Three failures on 2026-10-30 came from timing and the host, not from behavior:

- The Windows `host-conformance` leg of run 41000475638 failed with `WinError 32` while publishing
  Vale. `_materialize_native` runs the prepared `vale.exe` to qualify it and then moves it into the
  cache, but Windows still held the just-run image, so both the move and the scratch cleanup were
  refused.
- Two of `0.2.0-alpha.21`'s three local proofs stopped on
  `test_worktree_ref_holder_timeout_releases_owned_git_process`. Its 2-second deadline also covers
  preparing the reference transaction, including the fixture hook's start-up, which exceeds
  2 seconds under proof load. So the deadline expired before the test entered the hold it means to
  overrun.
- GitLab pipeline 13448's `verify` job stopped on
  `test_changed_bytes_under_a_restored_mtime_are_hashed_again`. The test turns off the memo's racy
  window and then rewrites a file within one filesystem timestamp tick of the recorded state. The
  CI guest's container filesystem then stamps the same ctime, so the memo correctly reuses the
  recorded digest, and the test's premise does not hold.

## What Changes

- Publishing a qualified native payload retries a Windows sharing violation for a bounded time.
  Qualification still precedes publication.
- The ref-holder timeout test uses a deadline that preparation fits under load, and its hold
  outlasts that deadline from the moment the hold is entered.
- The memo test waits until the filesystem stamps a later ctime than the recorded state before it
  rewrites the file. This is the precondition that the product's 2-second racy window guarantees.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement changes; `skip_specs: true` applies.

## Impact

`src/ethos/adapters/repo/runtime/materialization/native_supply.py` and three test modules change.
No packaged data, release note or adopter-visible behavior changes, except that a Windows
materialization no longer fails on a transient sharing violation.
