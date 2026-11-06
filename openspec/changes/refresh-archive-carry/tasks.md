# Tasks

## 1. Archive resolution

- [x] 1.1 Specify with a failing test that a fast-forward refresh past a rebased archive commit
      resolves that commit at its ancestry distance. Done when it fails on the current code. Red at
      05:41:12: the walk carried the rebased archive onto the fast-forward target at distance 0.
- [x] 1.2 Stop the walk at the first commit in current history. Done when that test and the archive
      provenance, recovery and change selection tests pass. Green at 05:43:19: 255 archive
      provenance, recovery, selection, admission and planning tests pass. With the fix,
      `ethos status` passes in both lanes at `e542a8909`, which refused with
      `openspec_archive_attestation_ambiguous` before.
