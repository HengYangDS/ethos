# Tasks

## 1. Refusal

- [x] 1.1 Bound the regression to mise 2026.11.0 and 2026.11.1. Done when tests show that 2026.11.0
      and 2026.11.1 name jdx/mise#15363 and mise 2026.11.2, and that 2026.11.2 names trust without
      the regression. The new cases fail first. The two new cases failed first: 2026.11.1 still said
      "before 2026.11.0" and 2026.11.2 still blamed #15363. With the bound, the 21 supply tests
      pass.

## 2. Specification and notes

- [x] 2.1 Modify the `quality` requirement on the locked supply refusal. Done when strict validation
      and the cumulative archive simulation pass. Strict validation and the archive simulation pass:
      1 requirement modified, 12 of 12 specifications valid.
- [x] 2.2 Name the change in the Unreleased notes. Done when `changelog_errors` reports nothing.
      `changelog_errors` reports nothing.
