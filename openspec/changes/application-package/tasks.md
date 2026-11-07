# Tasks

## 1. Package and moves

- [x] 1.1 Create `ethos.application` and move the five shared operations, and `domain/execution.py`
      as `invocation.py`, with `git mv`, rewriting every import and string patch target in `src/`,
      `tests/` and `tools/`. Done when a search for each old dotted path returns nothing and the
      moved modules' tests pass. At 00:08:14 the full suite passed, 8,289 tests with 4 skipped,
      after the moves and the rewrite of 45 files; at 00:08:49 a search of `src/`, `tests/`,
      `tools/`, `docs/`, `rules/`, `.config/` and `system/` for the old dotted and path forms
      returned nothing outside decision records.
- [x] 1.2 Move proof into `ethos.application.proof` as `prove_repository(root, request)`, returning
      each former rendering point's result. Done when an in-process test shows, for a refused mode
      and an unadopted repository, that the operation writes no stdout and returns the verdict,
      state, gaps and continuation that `ethos prove --json` renders, and the proof command tests
      pass with their patches pointed at the operation module. At 23:22:13
      `test_the_operation_returns_what_the_command_renders` passed for both cases with the 374
      proof, MCP and surface tests, the proof command tests patching
      `ethos.application.proof.operation`; `ethos prove --help` is identical before and after the
      move.

## 2. Contracts and documents

- [x] 2.1 Add the `application` layer and the three forbidden contracts with today's edges listed.
      Done when the import-boundaries gate passes and fails both on a new surface import of
      `ethos.adapters` and on a listed edge that no longer exists. At 23:19:00 `lint-imports` kept
      all four contracts with 69 and 9 listed edges; on a copy of `src/`, an added
      `ethos.surface.cli.version -> ethos.adapters.actor` broke the surface contract, and an added
      unmatched entry failed with "No matches for ignored import".
- [ ] 2.2 Update `docs/reference/command-plane.md`, `rules/module-layout.md` and `CHANGELOG.md`.
      Done when the docs gates pass.

## 3. Acceptance

- [ ] 3.1 Pass lint, the full test suite and readiness at the lane head. Done when each passes on
      the committed head.
