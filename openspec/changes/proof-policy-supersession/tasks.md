# Tasks

## 1. Reproduce

- [x] 1.1 Add a same-HEAD old-policy plus current-policy proof test and verify current repository-transition selection blocks despite a valid current record.
- [x] 1.2 Add negative cases for old-policy-only, explicit old selection, tampered binding and current-policy contradiction; verify their distinct gaps.

## 2. Repair

- [x] 2.1 Separate policy applicability from cross-record integrity at the existing proof reducer; verify current proof selection passes without deleting an old record.
- [x] 2.2 Run the complete affected proof-admission and publication tests; verify no weakened source, floor, intent or artifact boundary.

## 3. Verify source

- [x] 3.1 Run strict OpenSpec, repository format/lint, focused regressions and diff hygiene on the exact source; leave accepted-ref and adopter replay effects outside this checklist.
