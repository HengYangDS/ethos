# Tasks

## 1. Conflicting increment in fix mode

- [x] 1.1 Run the two conflict tests in check and fix mode. Done when each of the four cases
      reports `native_formatter_policy_conflict` with a block and leaves the selected files, the
      increment and the index unchanged. (The four cases pass in 7.5 seconds; the whole
      `test_source_format.py` passes, 46 cases.)
- [x] 1.2 Show that the fix cases distinguish. Done when, with the Prettier conflict check removed
      from `src/ethos/adapters/gates/formatting.py` in the worktree only, the Prettier fix case
      fails, and the restored file passes again with no diff. (The fix case then reported `pass`
      with state `formatted` and failed; the check case also failed, with only
      `source_format_drift` gaps; `git checkout` restored the file with no diff.)

## Workflow follow-up

- After the release that carries this Change is published and accepted, reply on GitHub issue 20
  with the test and its landed commit, and close it.
