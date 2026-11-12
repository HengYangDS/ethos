# Tasks

## 1. Admit the tutorial role

- [x] 1.1 Add `tutorial` to the registry's default roles. Done when a page with `role: tutorial`
      passes the registry and docs health, the test fails before the change, and the configuration
      reference and the Unreleased entry name it. `2f05224d0` adds `tutorial` to
      `DEFAULT_ROLE_VALUES`; the role test's new `tutorial` case failed before the change, the
      docs-health module then passed 62 tests, and the configuration reference and the Unreleased
      Added entry name the role.

## 2. Acceptance

- [ ] 2.1 Pass the impacted tests, the precheck and readiness at the lane head. Done when each
      passes on the committed head.
