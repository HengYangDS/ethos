# Tasks

The tasks below are the first slice of the row: the report. The design's Decisions 6, 8, 9 and 10
name the drafts that carry the rest.

## 1. The report's owner

- [ ] 1.1 In the Mise adapter, return the gaps of one search path from a function of its own, and
      add a reader that takes a launch path. Done when
      `test_a_launch_path_is_read_against_the_lock_without_a_refusal` in
      `tests/unit/adapters/toolchain/test_mise_supply.py` names a declared tool that a search path
      resolves outside its install, and the module's other tests pass unchanged.
- [ ] 1.2 Add `src/ethos/adapters/gates/child_environment.py` with the list of kept names of
      Decision 4, the four credential classes and the report of one launch environment. Done when
      `tests/unit/adapters/gates/test_child_environment.py` passes the seven cases of
      `test_a_launch_is_measured_against_the_list`, one for each class and one for kept names in
      another letter case among them, each on a repository without a lock and each comparing the
      whole report; and the three cases of
      `test_a_lock_is_read_or_named_unread_and_an_overlay_names_its_keys`, which read a lock, a
      refused lock and a failed read under an overlay of three keys and find no value of the
      launch in the report.
- [ ] 1.3 Name an executable's supplier in the same module. Done when each of the five suppliers
      has a case in that test module: three in `test_a_first_word_names_what_supplied_it` and
      two through the gate runner (task 3.1).

## 2. The result

- [ ] 2.1 Carry the executable and the supplier of a declared command from the gate runner to its
      check, and project both in the check's summary. Done when
      `test_run_plan_checks_executes_ready_checks_concurrently_in_plan_order` reads the runner's
      supplier from a check's summary and none from a planned check, and
      `test_host_focused_gate_executes_without_lease_or_proof_attestation` reads no supplier
      from a provider's check.
- [ ] 2.2 State `summary.environment` in a `prove` result that executed gates: a governed proof,
      a host observation and a readiness run. Done when `test_prove_result_matrix` finds the
      member in each executed result and in no planned one, the host test above reads it,
      `test_the_readiness_run_executes_only_the_tier_and_names_the_rest_not_run` finds it, and
      `test_host_admission_requires_committed_executable_source` finds none in an observation
      that ran no gate.
- [ ] 2.3 Hold the verdict apart from the report. Done when the host test above passes with a
      lock that cannot be read: the observation passes, its exit code is zero, and
      `locked_toolchain` is `unread:locked_toolchain_missing`.

## 3. The measured cases

- [ ] 3.1 Pin the third case. Done when
      `test_one_command_passes_from_two_launches_and_names_two_executables` runs one declared
      command through the gate runner under two launch paths and reads two executables and two
      passing verdicts, and its other two cases read `declared` for a repository path and for the
      bound interpreter.
- [ ] 3.2 Pin the first, sixth and seventh cases as reports. Done when
      `test_a_launch_is_measured_against_the_list` passes its three cases: a launch with Mise's
      activation state and one credential of each class, a launch with one further variable, and
      a launch of kept names alone, which reports zero outside the list.

## 4. Documents

- [ ] 4.1 State the boundary and the members in `docs/architecture/gate-runner.md`. Done when the
      page says that ETHOS does not confine a declared command, Prettier and the prose gate accept
      it, and the documentation registry reports no gap.
- [ ] 4.2 Add one Added entry to the Unreleased section of `CHANGELOG.md`. Done when it names
      `summary.environment`, the two members of a check, and that no child's environment changes.
- [ ] 4.3 Create the draft Changes `gate-child-environment`, `package-cache-root`,
      `gate-output-redaction` and `git-overlay-keys`, each a proposal without tasks that cites
      its place in the order, its decision of this design with the measured figures, its owner
      and the release that reads it again. Done when `openspec validate <name> --strict` passes
      for each of the four.
- [ ] 4.4 Amend the design contract's first sentence on a repository-declared command and add the
      mode's sentence to `docs/architecture/gate-runner.md`. Done when the contract page holds at
      most 500 non-blank lines, the documentation registry reports no gap and
      `tests/unit/repository/test_context.py` passes.

## 5. Lane-only acceptance

- [ ] 5.1 Run the tests that import a changed module, as the importers tool lists them, and the
      whole-repository guards, one module a run. Done when each run's result line is in the
      lane's record and none fails.
- [ ] 5.2 Run `tests/unit/adapters/gates/test_child_environment.py` and
      `tests/unit/adapters/toolchain/test_mise_supply.py` on Python 3.12 and 3.13: the supplier
      resolves a path and compares it with the locked installs. Done when both interpreters pass
      both.
- [ ] 5.3 Measure the three budget totals at the lane head. Done when the product total is at
      most 130 line-equivalents and the test total at most 150, the bounds that the lead set for
      this slice.
- [ ] 5.4 Read the owner's two decisions of 2026-11-17 in the proposals of
      `gate-child-environment` and `package-cache-root` against the owner's own words. Done when
      both texts say what the owner decided and nothing more.
- [ ] 5.5 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
- [ ] 5.6 Hand the full proof to the landing. Done when the Workflow follow-up states that the
      full proof runs on the archived head and that its receipt is the landing's.
- [ ] 5.7 Read the contract's amended sentence against the owner's answer. Done when the sentence in
      the lane is the one that the owner approved, word for word.

## Workflow follow-up

- The built environment of a declared command's child is carried by the draft Change
  `gate-child-environment`.
- The cache root is carried by the draft Change `package-cache-root`.
- Masking of persisted output is carried by the draft Change `gate-output-redaction`.
- The keys that local Git admits from the overlay are carried by the draft Change
  `git-overlay-keys`.
- Landing: the full proof runs on the archived head, and its receipt is the landing's.
