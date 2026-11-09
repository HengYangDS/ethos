# Tasks

## 1. Behaviour

- [x] 1.1 Require a version identity of every governed repository. Done when paradigm tests show an
      untagged repository without `VERSION` reported once, its repair naming a manifest's version,
      the tag pattern checked only with release tags, an untagged repository without `LICENSE`
      reporting no license gap, and the conforming tree carrying `VERSION` and a changelog. In the
      impacted sweep of 336 test files at `a76cb7db7` (19:38:11 to 20:37:47, 6,571 passed, 3 failed
      in other files, 2 skipped), every row of
      `test_a_releasing_repository_keeps_one_version_source_and_changelog`, the Python and npm
      projection rows among them, and `test_a_missing_version_names_the_manifest_version` passed.
- [x] 1.2 Seed only what no owner chooses. Done when a repair test creates an absent changelog and
      leaves a malformed one, and a formation test shows a formed repository with both files and no
      version-source or changelog gap. In the impacted sweep of 336 test files at `a76cb7db7`
      (19:38:11 to 20:37:47, 6,571 passed, 3 failed in other files, 2 skipped),
      `test_only_an_absent_changelog_is_created` and
      `test_greenfield_apply_forms_one_author_attributed_repository` passed.

## 2. Acceptance

- [x] 2.1 Pass the lane precheck, the impacted sweep and readiness at the committed head. Done when
      each passes there. The batch precheck passed with 0 findings at 20:51:27 to 20:51:49 against
      `0f788d4a6`, and readiness passed 28 gates from 20:46:13 to 20:51:07, both at `a12fcb313`. The
      impacted sweep of 336 test files at `a76cb7db7` passed 6,571 tests and failed 3 from 19:38:11
      to 20:37:47; `a12fcb313` fixed those 3, whose 2 files passed 16 tests from 20:45:41 to
      20:46:02, and the 34-file impacted sweep of the change since `a76cb7db7` passed 281 tests from
      20:43:26 to 20:45:09, both at `a12fcb313`.
