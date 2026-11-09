# Tasks

## 1. Selection

- [x] 1.1 Select the new families, the preview codes and the scoped ignores. Done when the
      configuration names each with its reason and Ruff loads it. `.config/checks/ruff/ruff.toml`
      selects ERA, T10, TD, FIX, EXE, INT, PYI, S, ANN, INP, T20, ICN and PLR0917 and the ten
      preview codes, and names each scoped ignore with its reason; Ruff loaded it for the 03:38:34
      run at `421f46a85`.

## 2. Fixes

- [x] 2.1 Fix the product and tool findings. Done when `ruff check` reports no finding over `src`,
      `tests` and `tools` and `ty` passes. At 03:38:34 at `421f46a85`, `ruff check --no-cache`
      reported no finding over `src`, `tests` and `tools`, and `ty` passed at 03:38:36. The 214
      findings measured at `5e83cfa5c` (29 S101, 118 ANN, 39 PLR0917, 3 S105 and 25 of ten preview
      rules) are fixed.

## 3. Acceptance

- [x] 3.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The precheck passed with 0 findings at 03:34:16 and readiness passed 29
      gates from 03:35:07 to 03:37:58, both at `421f46a85`. The impacted sweep of 415 test files ran
      from 01:56:07 to 02:23:32 on the Change's uncommitted tree: 7948 passed, 4 skipped and 22
      failed. The 22 came from test doubles of the old return shapes, a renamed constant and a
      signature read as text; `b15478bd8` fixed them, and their 5 files passed 73 tests from
      02:25:28 to 02:25:40.
