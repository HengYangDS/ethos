# Tasks

## 1. Effect marker deadline

- [x] 1.1 Make `kill_after_marker` wait for its marker within `seconds("tool")` and remove the
      callers' own deadlines. Done when the three modules that kill a child at its effect boundary
      pass and no caller passes a deadline. (`test_history_repair.py`,
      `test_merge_continuation.py` and `test_release.py` pass, 110 cases; no caller passes a
      deadline.)
