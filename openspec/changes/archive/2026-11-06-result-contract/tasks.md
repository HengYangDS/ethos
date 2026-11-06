# Tasks

## 1. Bounded results

- [x] 1.1 Specify the bound with failing tests. Done when tests fail for these cases: a `land`
      result over 16 KiB that keeps its failing steps inline; a result whose reduced form still
      exceeds the budget, which truncates with counts instead of raising; and the runner that
      expands detail.
- [x] 1.2 Apply one default budget to every command in `emit` and `apply_payload_budget`. Done when
      those tests and the command-plane tests pass.

## 2. Structured next step

- [x] 2.1 Specify `next` with failing tests: argv, effects, authorization and binding for a
      publish apply, a land closeout and a human decision. Done when they fail on the missing
      field.
- [x] 2.2 Add `NextStep`, derived from the rendered `next_action` with effects from the
      admission classification. Done when those tests pass and the test runner parses every
      structured next step of the command-plane tests with the live CLI.

## 3. Identity and schema

- [x] 3.1 Add runtime identity to every result and move the schema to version 3. Done when a test
      refuses a version-2 payload and every internal reader passes.
- [x] 3.2 Read bounded and predecessor results in the release tooling. Done when `invoke` reads a
      bounded result in full and a version-2 predecessor result as written.
