# Tasks

## 1. Unique content

- [x] 1.1 Specify with failing tests that housekeeping protects a detached worktree whose `HEAD` no
      retaining ref reaches, one that holds ignored files outside the regenerable roots, and one
      whose reachability Git cannot report. Also specify that a regenerable root still leaves it
      removable. Done when they fail on the current code. Red at 11:59:46: 4 of 8 failed. An
      unreachable `HEAD`, ignored content and unreachable Git all left the worktree removable; a
      root `.venv` already did.
- [x] 1.2 Check reachability and ignored content in the protection reasons. Done when those tests
      and the housekeeping and lane lifecycle tests pass. Green at 12:00:39: the 39 housekeeping
      tests pass. At 12:04:58 the 696 lane tests pass. Ty and ruff pass.
