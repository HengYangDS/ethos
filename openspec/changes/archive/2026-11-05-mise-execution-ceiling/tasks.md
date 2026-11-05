# Tasks

## 1. Execution

- [x] 1.1 Stop a gate child's mise at the repository's parent. Done when a native mise test, with an
      operator configuration that declares another tool above the repository, lists only the
      repository's declared tool. The test fails first. The native test failed first:
      `mise config ls --json` listed the operator configuration under the fixture home beside the
      repository. With the repository parent in the ceiling, only the repository configuration
      loads. A raw-mise probe showed the same with mise 2026.10.25. 100 toolchain and distribution
      tests and 141 tests of other `locked_environment` consumers pass.

## 2. Specification and notes

- [x] 2.1 Add the scenario to the `quality` requirement on locked execution. Done when strict
      validation and the cumulative archive simulation pass. Strict validation and the cumulative
      archive simulation of both Changes pass, with 12 of 12 specifications valid.
- [x] 2.2 Name the fix in the Unreleased notes. Done when `changelog_errors` reports nothing.
      `changelog_errors` reports nothing.
