# Tasks

## 1. Gate provider identity

- [x] 1.1 Compare a gate's provider references by the provider each names. Done when
      `test_gate_executor_malformed_shapes_fail_closed` refuses an ID with its legacy name among the
      providers and among the verification providers, and
      `test_gate_names_distinct_providers_under_any_spelling` accepts two providers under different
      spellings and two names that the catalog lacks. Evidence: lane commit `38f22a2b5`; in the
      preparation clone on the base's product code the two cases did not raise. The gate registry
      tests passed in the lane among 409 tests of 19 modules at `ec33ac087` (02:18:43).
- [x] 1.2 Hold a verification provider reference in the gate schema to the form and the unique items
      of a provider reference. Done when
      `test_gate_schema_holds_a_verifier_reference_as_the_model_does` passes and Prettier accepts
      the schema. Evidence: lane commit `38f22a2b5`; in the preparation clone on the base's product
      code the schema accepted both references. The schema tests passed in the lane run that task
      1.1 names.

## 2. Gap registry

- [x] 2.1 Return a copy of a row from the registry's two row readers. Done when
      `test_a_row_handed_to_a_reader_is_its_own_copy` passes. Evidence: lane commit `38f22a2b5`; the
      gap registry guard passed in the lane run that task 1.1 names.
- [x] 2.2 Record the family-prefix measurement as the draft Change `gap-code-literals`. Done when
      its proposal states the measured counts, its owner, its next action and its review date, and
      `openspec validate gap-code-literals --strict` passes. Evidence: lane commits `6cf31dc60` and
      `048d61d44`.

## 3. Documents

- [x] 3.1 Add the changelog entry under Unreleased, Fixed. Done when Prettier and the prose gate
      accept `CHANGELOG.md`. Evidence: lane commit `38f22a2b5`; Prettier and Vale accepted the file
      at the commit, and the prose gate is among the gates of the readiness run: readiness passed 28
      gates with none failing at 03:26:10.

## 4. Acceptance

- [x] 4.1 Pass the focused gates on the lane head: the test modules that import a changed module,
      the seven whole-repository guards, Ruff, ty, import-linter,
      `openspec validate gate-provider-identity --strict` and Prettier. Done when each reports no
      finding. Evidence: at `da63d1e11` the static precheck passed with no finding at 02:24:07
      (Ruff, import-linter, strict OpenSpec validation, Prettier); readiness passed 28 gates with
      none failing at 03:26:10, the type check among them; the seven guards passed in the lane run
      that task 1.1 names; and the whole suite passed on the forges: GitHub run 43746618955 and
      GitLab pipeline 15865 of `da63d1e11` passed every job, read at 03:04:38.
- [x] 4.2 Measure the source budget against the lane base. Done when the measured figures are
      recorded beside the preparation's: product +6.4 and tests +51.8 line-equivalents. Evidence:
      measured on the lane between `ca2f73972` and `38f22a2b5`: product +6.4, tests +51.8 and tools
      +0.0 line-equivalents, equal to the preparation's.

## 5. Lane, hosted and owner tasks

- [x] 5.1 Pass the precheck and readiness on the committed lane head. Done when each passes.
      Evidence: at `da63d1e11` the static precheck passed with no finding at 02:24:07, and readiness
      passed 28 gates with none failing at 03:26:10.
