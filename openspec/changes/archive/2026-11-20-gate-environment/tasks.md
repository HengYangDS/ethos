# Tasks

The tasks below are the first slice of the row: the report. The design's Decisions 6, 8, 9 and 10
name the drafts that carry the rest.

## 1. The report's owner

- [x] 1.1 In the Mise adapter, return the gaps of one search path from a function of its own, and
      add a reader that takes a launch path. Done when
      `test_a_launch_path_is_read_against_the_lock_without_a_refusal` in
      `tests/unit/adapters/toolchain/test_mise_supply.py` names a declared tool that a search path
      resolves outside its install, and the module's other tests pass unchanged.
      (At `f72816530` the case passes, and the module's 26 cases pass under Python 3.12, 3.13 and
      3.14.)
- [x] 1.2 Add `src/ethos/adapters/gates/child_environment.py` with the list of kept names of
      Decision 4, the four credential classes and the report of one launch environment. Done when
      `tests/unit/adapters/gates/test_child_environment.py` passes the seven cases of
      `test_a_launch_is_measured_against_the_list`, one for each class and one for kept names in
      another letter case among them, each on a repository without a lock and each comparing the
      whole report; and the three cases of
      `test_a_lock_is_read_or_named_unread_and_an_overlay_names_its_keys`, which read a lock, a
      refused lock and a failed read under an overlay of three keys and find no value of the
      launch in the report.
      (At `f72816530` the seven cases and the three cases pass; the module holds 18 cases.)
- [x] 1.3 Name an executable's supplier in the same module. Done when each of the five suppliers
      has a case in that test module: three in `test_a_first_word_names_what_supplied_it` and
      two through the gate runner (task 3.1).
      (At `f72816530`: `unresolved`, `locked` and `host-baseline` in the three cases of
      `test_a_first_word_names_what_supplied_it`; `launch-path` and `declared` through the gate
      runner in the three cases of task 3.1.)

## 2. The result

- [x] 2.1 Carry the executable and the supplier of a declared command from the gate runner to its
      check, and project both in the check's summary. Done when
      `test_run_plan_checks_executes_ready_checks_concurrently_in_plan_order` reads the runner's
      supplier from a check's summary and none from a planned check, and
      `test_host_focused_gate_executes_without_lease_or_proof_attestation` reads no supplier
      from a provider's check.
      (At `f72816530` the first test passes its 3 cases and the second its 2.)
- [x] 2.2 State `summary.environment` in a `prove` result that executed gates: a governed proof,
      a host observation and a readiness run. Done when `test_prove_result_matrix` finds the
      member in each executed result and in no planned one, the host test above reads it,
      `test_the_readiness_run_executes_only_the_tier_and_names_the_rest_not_run` finds it, and
      `test_host_admission_requires_committed_executable_source` finds none in an observation
      that ran no gate.
      (At `f72816530`: `test_prove_result_matrix` passes 7 cases, the host test 2, the readiness
      test 2 and the admission test 2.)
- [x] 2.3 Hold the verdict apart from the report. Done when the host test above passes with a
      lock that cannot be read: the observation passes, its exit code is zero, and
      `locked_toolchain` is `unread:locked_toolchain_missing`.
      (At `f72816530` the host test's two cases read `unread:locked_toolchain_missing` and keep the
      provider's verdict and exit code.)

## 3. The measured cases

- [x] 3.1 Pin the third case. Done when
      `test_one_command_passes_from_two_launches_and_names_two_executables` runs one declared
      command through the gate runner under two launch paths and reads two executables and two
      passing verdicts, and its other two cases read `declared` for a repository path and for the
      bound interpreter.
      (At `f72816530` the three cases pass: two launch paths give two executables, two passing
      verdicts and `launch-path`; a repository path and the bound interpreter read `declared`.)
- [x] 3.2 Pin the first, sixth and seventh cases as reports. Done when
      `test_a_launch_is_measured_against_the_list` passes its three cases: a launch with Mise's
      activation state and one credential of each class, a launch with one further variable, and
      a launch of kept names alone, which reports zero outside the list.
      (At `f72816530` the three cases are among the seven of task 1.2 and pass.)

## 4. Documents

- [x] 4.1 State the boundary and the members in `docs/architecture/gate-runner.md`. Done when the
      page says that ETHOS does not confine a declared command, Prettier and the prose gate accept
      it, and the documentation registry reports no gap.
      (At `f72816530` the page states the boundary, the members and the mode. Markdown lint and the
      prose gate pass, and both refuse a control; the documentation registry reports no gap; 11
      local links resolve.)
- [x] 4.2 Add one Added entry to the Unreleased section of `CHANGELOG.md`. Done when it names
      `summary.environment`, the two members of a check, and that no child's environment changes.
      (The entry is under Added in the unreleased section at `f72816530` and names the three.)
- [x] 4.3 Create the draft Changes `gate-child-environment`, `package-cache-root`,
      `gate-output-redaction` and `git-overlay-keys`, each a proposal without tasks that cites
      its place in the order, its decision of this design with the measured figures, its owner
      and the release that reads it again. Done when `openspec validate <name> --strict` passes
      for each of the four.
      (The four proposals validate strictly at `9fada8291`.)
- [x] 4.4 Amend the design contract's first sentence on a repository-declared command and add the
      mode's sentence to `docs/architecture/gate-runner.md`. Done when the contract page holds at
      most 500 non-blank lines, the documentation registry reports no gap and
      `tests/unit/repository/test_context.py` passes.
      (At `f72816530` the contract page holds 500 non-blank lines, the registry reports no gap and
      the module's 18 cases pass.)

## 5. Lane-only acceptance

- [x] 5.1 Run the tests that import a changed module, as the importers tool lists them, and the
      whole-repository guards, in runs of at most two minutes. Done when each run's result line
      is in the lane's record and none fails.
      (With the tree of `f72816530`: 38 modules, 1,069 cases in 17 runs, none failed and none
      skipped; the 40 architecture test files pass in four runs, 311 cases and 1 skipped. Two listed
      modules belong to later rows and are not in the lane. One module passes two minutes alone and
      ran by test function and by case. The result lines are in the kit's test log under the labels
      `r9*` and `arch-r9*`.)
- [x] 5.2 Run `tests/unit/adapters/gates/test_child_environment.py` and
      `tests/unit/adapters/toolchain/test_mise_supply.py` on Python 3.12 and 3.13: the supplier
      resolves a path and compares it with the locked installs. Done when both interpreters pass
      both.
      (With the tree of `f72816530`: 44 cases pass under Python 3.12 and under 3.13.)
- [x] 5.3 Measure the three budget totals at the lane head. Done when the product total is at
      most 130 line-equivalents and the test total at most 150 for the slice as built and 180
      with the two cases that the lead's review added, the bounds that the lead set for this
      slice.
      (From `39cb01abb` to `f72816530`: product 83,206 to 83,333, which is 127; tests 109,724 to
      109,900, which is 176, 150 as built and 26 for the two cases of a command that did not finish;
      tools 8,908 unchanged.)
- [x] 5.4 Read the owner's two decisions of 2026-11-17 in the proposals of
      `gate-child-environment` and `package-cache-root` against the owner's own words. Done when
      both texts say what the owner decided and nothing more.
      (Read on 2026-11-19 against the record of the owner's answers and the page as it stood when
      the owner answered. `gate-child-environment` named design points under the owner's decision,
      and `package-cache-root` named two that the page had not shown. Both now list the owner's
      decision apart from the design, at `d55a7fc85` and `cdcd7cf34`.)
- [x] 5.5 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
      (At `7bd573ad9` on 2026-11-20 the pre-check passes with no finding and readiness passes with
      its 28 gates. The pre-check ran its full selection at `a9e90ab6f`, 413 test modules, 8,337
      passed and 3 skipped, and from there the selection of the one test file that differs, 43
      modules, 371 passed and 1 skipped.)
- [x] 5.6 Hand the full proof to the landing. Done when the Workflow follow-up states that the
      full proof runs on the archived head and that its receipt is the landing's.
      (The Workflow follow-up below states it.)
- [x] 5.7 Read the contract's amended sentence against the owner's answer. Done when the sentence in
      the lane is the one that the owner approved, word for word.
      (At `f72816530` the page holds the sentence that the record of the owner's answer of
      2026-11-17 holds, word for word.)

## Workflow follow-up

- The built environment of a declared command's child is carried by the draft Change
  `gate-child-environment`.
- The cache root is carried by the draft Change `package-cache-root`.
- Masking of persisted output is carried by the draft Change `gate-output-redaction`.
- The keys that local Git admits from the overlay are carried by the draft Change
  `git-overlay-keys`.
- Landing: the full proof runs on the archived head, and its receipt is the landing's.
