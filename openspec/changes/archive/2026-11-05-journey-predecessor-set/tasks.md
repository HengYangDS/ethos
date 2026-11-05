# Tasks

## 1. Journey

- [x] 1.1 Validate named predecessors. Done when tests show that a name in the wrong form, a name
      that is not an earlier changelog entry and an unpublished release each refuse with their tag,
      that duplicates collapse, and that the result follows changelog order. The tests fail first.
      The new tests failed first: `named_predecessors` did not exist. Now a malformed, later,
      unknown and unpublished name each refuse with their tag, and duplicates collapse in changelog
      order.
- [x] 1.2 Upgrade from each predecessor in its own host store. Done when a test qualifies a tag from
      two named predecessors and reads both in `previous`, one `assets` entry per version and
      `upgrade_and_rollback` keyed by predecessor tag. A test without names still reads the latest
      published predecessor and its skipped entries. The two-predecessor test reads
      `["v0.2.0-alpha.28", "v0.2.0-alpha.27"]` in `previous`, three `assets` entries, both tags in
      `upgrade_and_rollback` and two distinct `XDG_DATA_HOME` stores. The default test still reads
      alpha.27 and the skipped alpha.28.
- [x] 1.3 Pass the predecessors from the dispatch. Done when the session splits `--previous` on
      commas and the architecture test reads the `journey_previous` input, its empty default and the
      environment-bound `--previous "$JOURNEY_PREVIOUS"` step in the projected workflow. The session
      test passes `("v0.2.0-alpha.29", "v0.2.0-alpha.30")` from
      `"v0.2.0-alpha.29, v0.2.0-alpha.30,"` and nothing from an empty value. The architecture test
      reads the input, its empty default and the step environment. 256 CI delivery and architecture
      tests pass.

## 2. Specification and notes

- [x] 2.1 Modify the `distribution` requirements on the beta criterion, the hosted journey and the
      predecessor selection. Done when strict validation and the cumulative archive simulation pass.
      Strict validation and the cumulative archive simulation pass: 2 requirements added, 3
      modified, 12 of 12 specifications valid.
- [x] 2.2 Describe `journey_previous` in the release guide and name the change in the Unreleased
      notes. Done when `changelog_errors` reports nothing. `changelog_errors` reports nothing.
