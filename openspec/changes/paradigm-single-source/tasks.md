# Tasks

## 1. Formatter baseline

- [x] 1.1 Report no formatter gap for an untracked carrier and keep the setting check for a tracked
      one. Done when a fixture without carriers passes and one with a contradicting setting is
      refused. (Covered in `test_paradigm_report.py`.)
- [x] 1.2 Retire formatter-carrier creation from repair. Done when repair still corrects a setting
      and has no handler for a missing carrier. (Covered in `test_paradigm_repair.py`.)

## 2. Version projection

- [x] 2.1 Accept a root `package.json` `version` equal to `VERSION` and keep the gap for any other
      value or without `VERSION`. Done when the three cases are covered. (Covered in
      `test_paradigm_conventions.py`.)

## 3. Specification

- [x] 3.1 Replace the formatter requirement and amend the version requirement in the
      `repository-paradigm` delta. Done when strict validation passes. (It passes.)
