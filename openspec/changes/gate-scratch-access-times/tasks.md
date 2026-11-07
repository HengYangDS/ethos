# Tasks

## 1. Renewed access times

- [x] 1.1 Specify with failing tests that the access-time renewal keeps each modification time,
      renews the access time, and never follows a directory symlink. Also specify that the probe
      syncs, then runs without syncing, and reports a failed sync as `test_environment_sync_failed`.
      Done when they fail on the current code. Red at 11:35:57: 6 of 34 tests failed. The renewal
      was missing, the probe ran once without syncing, and a failed sync reported
      `test_command_failed`.
- [x] 1.2 Sync, renew and run in the behavior probe, and use `shutil.copy` in the gitleaks mirror
      and the fixture copies. Done when those tests and the Python quality evidence tests pass.
      Green at 11:43:38: 1,253 quality, gate, status-projection and CI tests pass with 1 skip. At
      11:55:33 the 57 modules that use the changed fixture support pass with 1,338 tests and 1 skip.
      Ty and ruff pass.
