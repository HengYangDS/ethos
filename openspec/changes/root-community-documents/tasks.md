# Tasks

## 1. Admit the community health files

- [x] 1.1 Add `ACCESSIBILITY.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md` and `SUPPORT.md` to the root
      catalog's entry documents. Done when a conforming tree with all four passes the paradigm
      report, the test fails before the change, and the 0.2.0-beta.8 entry's Added line names them.
      In `3e3679040` the new test found four `repository_paradigm_root_catalog` gaps before the
      change, one per name; after it the paradigm report passes, the module's 75 tests pass, and the
      0.2.0-beta.8 entry's Added line names the four files.

## 2. Acceptance

- [x] 2.1 Pass the impacted tests with `tests/architecture`, the precheck and readiness at the lane
      head. Done when each passes on the committed head. At `3e3679040` the 145 affected test
      modules with `tests/architecture` passed, 3,550 passed and 1 skipped by design (a
      gate-efficacy test judged only on the whole suite); the static precheck passed with no
      finding, and readiness passed 28 of 28 gates.
