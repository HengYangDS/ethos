# Tasks

## 1. One TOML renderer in the shipped layout

- [ ] 1.1 Render governed TOML with the shipped Taplo indent. Done when a repaired `record_roots`
      array is two-space indented and byte-equal to the shipped Taplo's formatting of it, the test
      fails before the change, and the paradigm repair and the profile renderer call one function.
- [ ] 1.2 Move the defect in the 0.2.0-beta.8 entry from the known open defects to Fixed. Done when
      the entry names it only under Fixed and no other line of `CHANGELOG.md` changes.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests with `tests/architecture`, the precheck and readiness at the lane
      head. Done when each passes on the committed head.
