# Tasks

## 1. One TOML renderer in the shipped layout

- [x] 1.1 Render governed TOML with the shipped Taplo indent. Done when a repaired `record_roots`
      array is two-space indented and byte-equal to the shipped Taplo's formatting of it, the test
      fails before the change, and the paradigm repair and the profile renderer call one function.
      In `4902b19ad` the extended record-binding test failed before the change on four spaces
      against two, and `test_toml_layout.py` could not import the renderer; after it both modules
      pass, 10 tests, with the lane's Node runtime, the shipped Taplo leaves a rendered profile
      unchanged, and the three repair sites and the profile renderer call `render_toml`.
- [x] 1.2 Move the defect in the 0.2.0-beta.8 entry from the known open defects to Fixed. Done when
      the entry names it only under Fixed and no other line of `CHANGELOG.md` changes. In
      `4902b19ad` the defect left the known open defects and the entry's Fixed list names the
      change; that commit changes no other line of `CHANGELOG.md`.

## 2. Acceptance

- [x] 2.1 Pass the impacted tests with `tests/architecture`, the precheck and readiness at the lane
      head. Done when each passes on the committed head. At `3e3679040` the 145 affected test
      modules with `tests/architecture` passed, 3,550 passed and 1 skipped by design (a
      gate-efficacy test judged only on the whole suite); the static precheck passed with no
      finding, and readiness passed 28 of 28 gates.
