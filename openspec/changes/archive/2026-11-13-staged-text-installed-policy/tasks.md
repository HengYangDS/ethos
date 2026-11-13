# Tasks

## 1. Staged text check

- [x] 1.1 Read the canonical-text rows from the shipped policy in the staged text check. Done when
      the regression test fails before the change and passes after it, and the hook tests pass.
      Evidence: the regression test failed before the change with
      `format_selection_increment_invalid` (06:15:13 to 06:15:21), the error that refused every
      ETHOS commit after batch 3 landed, and passed after it with the hook tests and the
      architecture suite (614 passed, 1 skipped, 06:16:10 to 06:19:02); Ruff and ty passed.
