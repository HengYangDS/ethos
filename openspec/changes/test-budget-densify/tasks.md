# Tasks

## 1. Densify

- [x] 1.1 Replace repeated calls with module-local helpers and runs of field assertions with tuple
      assertions. Done when the changed modules' tests pass and `python_tests` measures at most
      94,880 effective lines. At 23:34: python_tests went from 95,115 to 94,849; the 171 tests of
      the ten changed modules pass.
