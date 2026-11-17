# Tasks

## 1. The selection

- [ ] 1.1 Give the deleted-input join and the selection one reader of a file's imports,
      `imported_modules` in `references/python_syntax.py`. Done when the join's tests in
      `tests/unit/repository/policy/references/` pass unchanged.
- [ ] 1.2 `select_tests` in `policy/quality/selection.py` returns each test that reads a changed
      path with its strongest reason, and the changed paths that no test reads. Done when the nine
      cases of `test_a_change_selects_its_readers_and_names_the_paths_without_one` pass, among
      them a document that a test names and a file two imports away that is not selected.
- [ ] 1.3 `carried_paths` reads the wheel's carried-file table of the Python manifest, reads a
      manifest without one as carrying nothing and raises the error of one that cannot be parsed.
      Done when its four cases and the refusal in
      `test_the_carried_paths_come_from_the_wheel_table_or_are_none` pass.
- [ ] 1.4 Keep the case of 2026-11-15 as a regression on this repository's own files. Done when
      `test_a_carried_document_of_this_repository_selects_the_tests_that_stage_the_package` selects
      two staging tests and one naming test for the command reference.

## 2. The sessions that only a Forge runs

- [ ] 2.1 `forge_only_sessions` in `paradigm/orchestration.py` reads both Forges' pipeline files
      through `ci_steps` and returns the count of jobs read and each session that a step asks for
      and no planned command does. Done when
      `test_a_session_that_only_a_forge_job_asks_for_is_listed_with_its_jobs` passes with a
      continued line, two commands on one line and a step that runs another tool.
- [ ] 2.2 Refuse to read a tracked pipeline file that is gone as an empty one. Done when
      `test_forge_sessions_are_none_without_a_pipeline_and_refuse_an_unreadable_one` passes.

## 3. The readiness result

- [ ] 3.1 `readiness_unexamined` in `application/proof/unexamined.py` reports the selection of a
      Work Lane against its candidate branch and the session list, each part on its own, and
      names a part that cannot be read under `unavailable`. Done when the three cases of
      `test_the_readiness_result_names_what_it_did_not_examine` pass: a lane, a role without a
      base, and a base that does not resolve, each with the verdict of its gates.
- [ ] 3.2 `readiness_observation` carries the report as `data.unexamined` with the gates not run.
      Done when both cases of
      `test_the_readiness_run_executes_only_the_tier_and_names_the_rest_not_run` assert it, and
      the run on this repository's real policy lists `host_conformance` and `hosted_verification`.

## 4. Documents

- [ ] 4.1 State the field, its reasons and its limits in the Proof Depth section of the command
      reference, with the sentence that a passing readiness run is neither the full proof's pass
      nor the Forges' pass. Done when the page passes Prettier and the documentation registry and
      stays under 500 nonblank lines.
- [ ] 4.2 Add the entry to the unreleased changelog. Done when it names `data.unexamined`.

## 5. Lane, hosted and owner tasks

- [ ] 5.1 Run `ethos prove --readiness --execute --expect-head <head> --json` on the Work Lane
      that carries this Change. Done when its result holds `data.unexamined` with the lane's
      base, a selection for the lane's own changed paths and the six sessions of the base.
- [ ] 5.2 Run the tests that import a changed module and did not fit a two-minute run outside the
      queue, under a host ticket. Done when each module of the report's list passes.
- [ ] 5.3 Run the tests of sections 1 to 3 on Python 3.12 and 3.13. Done when they pass on both:
      the report adds one Git call and reads files, which the 3.14 run alone does not cover.
- [ ] 5.4 Pass the lane's pre-check, the full proof and the hosted runs on both Forges. Done when
      each passes at the lane head.
