# Tasks

## 1. Owner and location

- [x] 1.1 Serve a memo only from a directory and file that the current user owns and that group
      and others cannot write, create the directory with mode `0700`, and let a save tighten an
      owned directory that is looser. Done when tests show that a group-writable memo file, a memo
      owned by another user ID and a symbolic-link directory each make every file hash, that an
      owned memo is still reused and that a save tightens a looser owned directory, and each new
      test failed before the change. Before it, the three refusals hashed 0 files instead of 3 and
      the directory kept mode `0775`; with it, the module's 18 tests pass.

## 2. Failed saves

- [x] 2.1 Remove the temporary file on every failed save, after closing its stream. Done when a
      test shows that a save whose replace fails leaves no temporary file and raises nothing, and
      the test failed before the change. Before it, the save left `.o_1z51pl.tmp` beside the
      occupied memo path.

## 3. Release notes and checks

- [x] 3.1 Name the fix in the Unreleased notes. Done when the changelog validates and Ruff, ty, the
      module's tests and `tests/unit/adapters/repo/runtime` pass. Ruff and ty pass, and the
      runtime tests pass: 517, 1 skipped.
