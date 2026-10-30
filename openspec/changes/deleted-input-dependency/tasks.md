# Tasks

## 1. Admission

- [x] 1.1 Add deleted-input cases for a package that a project dependency, an optional dependency
      or a dependency group of the same normalized name provides, for the project's own package
      and for a dependency of another name, to
      `tests/unit/admission/test_patch_admission_public_fail_closed.py`. Done when the provided
      cases fail before the change and the blocking cases pass. (The three provided cases
      failed and the four blocking cases passed.)
- [x] 1.2 Let `PythonManifest` list its dependency distributions without the project's own name,
      and remove the deletions they provide from the Python import join in `deleted_input_gaps`.
      Done when the new and the existing deleted-input cases pass. (All 29 cases of the module
      pass.)
- [x] 1.3 Record the fix under `[Unreleased]` in `CHANGELOG.md`. Done when the entry names the
      admitted replacement and the cases that still block.

## 2. Verification

- [x] 2.1 Run the test modules that import `observation.py` or `manifests.py`. Done when they pass.
      (With `tests/unit/admission` and `tests/unit/repository/policy`, 865 tests pass.)

## Workflow follow-up

- Archive this Change with the lane's other Changes and prove the archived head once.
- After the release that carries it, tell the adopter lane that reported the block to rerun its
  prewrite.
