# Tasks

## 1. Integration

- [x] 1.1 Take the binary scan's waits from declared parameters. Done when `test_declared_timeouts`,
      which failed at `8f94e39c3`, passes, and the binary scan tests pass. The test failed at
      `8f94e39c3` with 34 literal waits in `tools/` against 31. With the three declared waits it
      passes, and so do the 36 binary scan tests.
- [x] 1.2 Add DR-0018's `Evidence and Revisit` section. Done when
      `test_decision_records_preserve_complete_cross_change_rationale` passes. The decision record
      test failed with `docs_decision_sections_invalid` for DR-0018; with the section it passes.
