# Tasks

## 1. Windows runtime path

- [x] 1.1 Name the release archive's runtime directory with the 16-digit digest prefix in
      `tools/ci/delivery/distribution.py`. Done when the path-budget test in
      `tests/unit/ci/delivery/test_distribution.py` holds the Windows interpreter path within 64
      characters and failed on the 96-character layout. (96 characters before, 48 after.)
- [x] 1.2 Let archive carriers resolve the prefix to the full digest from the runtime manifest, with
      the host store and its selectors still strict. Done when the selection, host store, input
      resolution and version tests pass with both directory names and refuse a wrong prefix.

## 2. Published archive compensation

- [x] 2.1 Refuse compensation while a peer's latest recorded publication selects the archived head.
      Done when `tests/unit/lanes/lifecycle/archive/test_compensation.py` refuses that case with
      `openspec_archive_published:fixture-change`, zero effect and the proposal retirement as the
      next action.

## 3. Byte-bound carriers and the code ceiling

- [x] 3.1 Receive the repository's validated byte-bound carriers with Git's vendored and generated
      paths in one paradigm classifier. Done when `tests/unit/adapters/gates/test_source_format.py`
      receives a verified carrier, does not receive it under an invalid increment, and the existing
      received-path tests of `tests/unit/repository/test_paradigm_report.py` pass.

## 4. Documentation and verification

- [x] 4.1 Record the three changes in `CHANGELOG.md` under Unreleased and describe the carrier
      exemption in `rules/module-layout.md`. Done when the prose and docs gates pass.
- [x] 4.2 Run every test module that imports a changed module. Done when they pass. (157
      modules, 3,629 tests, 1 skipped.)
- [x] 4.3 Measure the product source budget. Done when the Python product total is at most 70,000
      effective lines and every touched file is within 500. (69,978; largest touched file 499.)
