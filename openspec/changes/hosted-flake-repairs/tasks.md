# Tasks

## 1. Native publication on Windows

- [x] 1.1 Retry a Windows `PermissionError` while `_materialize_native` moves a qualified member
      into the cache, every 100 ms for at most 5 seconds, keeping qualification before publication.
      Done when a test in `tests/unit/adapters/repo/runtime/materialization/test_native_supply.py`
      shows that a transient refusal on Windows publishes the payload, and that the same refusal
      on POSIX raises at once.
      (Without the fix the Windows case fails with the `PermissionError`; with it both cases
      and the 34 existing native-supply tests pass, and Ruff passes.)

## 2. Deterministic timing tests

- [x] 2.1 Make `test_worktree_ref_holder_timeout_releases_owned_git_process` use a 5-second
      deadline and hold for the deadline plus a margin from entry. Done when the test passes alone
      and with the suite's parallel workers.
      (The test failed proofs p1 and p2 of `0.2.0-alpha.21` with `entered` unset; it passes
      alone with the change. The proof runs it with the parallel workers.)
- [x] 2.2 Make `test_changed_bytes_under_a_restored_mtime_are_hashed_again` wait until a probe
      file outside the payload stamps a later ctime than the recorded state before it rewrites the
      file. Done when the test passes and the memo module's other tests still pass.
      (It failed GitLab pipeline 13448's `verify` on the CI guest with `hashes.count` 0; the
      memo module's tests pass with the change on macOS. The guest's result comes with the
      landed head's GitLab run.)

## Workflow follow-up

- Archive this Change, prove the archived head once, then land, close out, bootstrap and publish
  `dev` to GitHub and GitLab. Read the landed head's hosted Windows and GitLab `verify` results.
