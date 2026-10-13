# Tasks

## 1. Deadline test

- [x] 1.1 Drive `test_command_scope_conserves_one_deadline_across_native_calls` from the adapter clock; done when it asserts the nested command's exact remaining timeout and passes under parallel test load.

## 2. Archive diagnostics

- [x] 2.1 Project blocking native issues of invalid validation items in `validation.py`; done when unreadable output yields no diagnostics.
- [x] 2.2 Carry those issues on the compensated archive result and forward them as CLI diagnostics; done when the archive boundary test asserts them with gaps and continuation unchanged.

## 3. Verify

- [x] 3.1 Run strict OpenSpec validation, Ruff, ty and the affected process, archive and lifecycle CLI tests; done when all pass with no unrelated tracked change.
