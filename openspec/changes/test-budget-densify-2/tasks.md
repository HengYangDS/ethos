# Tasks

## 1. Collapse

- [x] 1.1 Format the test tree once with `skip-magic-trailing-comma = true` and keep the result with
      the repository's formatter. Done when every changed module parses to the same syntax tree as
      before, ruff check and the repository's `ruff format --check` pass, and `python_tests`
      measures at most 93,200 effective lines. At 11:09: 210 modules changed, each with the same
      `ast.dump` as before; ruff check and the repository's `ruff format --check` pass from the lane
      root; `python_tests` went from 94,986 to 93,159, freeing 1,827 effective lines.
- [x] 1.2 Run the architecture tests and the support-dependent unit areas. Done when they pass. At
      11:10:33 the 273 architecture tests passed, and at 11:30:55 the 195 changed test modules
      passed with 4,706 tests and 1 skip.
