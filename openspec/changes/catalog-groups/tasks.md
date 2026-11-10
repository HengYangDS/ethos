# Tasks

## 1. S1: catalog machinery, attestation and host run

- [ ] 1.1 Spike the two unspiked cases in owned scratch. Done when the `process` exit and
      `lane prewrite --patch -` stdin both work through a generated signature, with the five earlier
      spike cases re-run on the real adapter.
- [ ] 1.2 Generate the golden `next` data with the uncommitted generator. Done when one JSON file
      under `tests/fixtures/` holds `(argv, effects, authorization, destructive, exit kind)` for
      every leaf and its mode-bearing flag subsets, and the test docstring records its provenance.
- [ ] 1.3 Complete the attestation and `host run` audit rows. Done when each ignored or checked flag
      has its exit before and after in the design's audit, with the product callers searched.
- [ ] 1.4 Add path keys, `GROUPS`, `modes()`, the field types S1 uses and the `process` exit kind.
      Done when `select_argv` selects a three-word path with positionals and `--`, and the table
      test passes over every path.
- [ ] 1.5 Build the generic group adapter and the full-path usage refusal. Done when the
      `(argv, command, exit)` table and the missing-required-field test pass for every migrated
      path.
- [ ] 1.6 Convert `attestation` and `host run` to entries. Done when their CLI tests pass through
      the adapter, `host run` exits with its child's status, and the 5 rows and 1 destructive row
      leave.
- [ ] 1.7 Fence part 1 and its test. Done when the listed S1 prefixes are in
      `src/ethos/adapters/admission/control/replacement.py` and the prefix test passes.
- [ ] 1.8 Record S1 deltas. Done when the measured kernel import cost, product delta (at most +110)
      and test delta (at most +100) are written in this task and the owner's fence acknowledgement
      is named.

## 2. S2: hook

- [ ] 2.1 Add the `hook` audit rows. Done when every hook flag combination that changes from ignored
      to refused is listed with its product callers.
- [ ] 2.2 Convert the 7 `hook` leaves to entries with `A/hook/` halves. Done when `S/hook/` is gone,
      `hook commit-range --check peer-identity` selects, and the golden data passes for the group.
- [ ] 2.3 Retarget the hook tests and the fence. Done when the 14 rows and 3 destructive rows leave,
      `test_activation.py` passes, and the hook and retention prefixes are fenced.
- [ ] 2.4 Record S2 deltas. Done when product (+10) and test (-60) deltas are written.

## 3. S3: lane lifecycle and repair

- [ ] 3.1 Add the audit rows for the 13 leaves. Done when each is listed with its callers.
- [ ] 3.2 Convert `lane` status, housekeeping, candidate, prewrite, start, refresh-base,
      archive-change, project, format, repair-paradigm, trust-commit-signer, repair-signature and
      redact. Done when `--paths X`, the `=` form and stdin work through the real CLI.
- [ ] 3.3 Retarget the lane tests, the fence and the import-set test. Done when the 18 rows and 2
      destructive rows leave and `lane prewrite` builds no other group's application half or App.
- [ ] 3.4 Record S3 deltas and the `lane prewrite` start-time measurement. Done when product (+50)
      and test (-80) deltas are written.

## 4. S4: lane retire, handoff, lease

- [ ] 4.1 Add the audit rows for the 13 leaves. Done when each is listed with its callers.
- [ ] 4.2 Convert `lane retire`, `handoff` and `lease`. Done when the receipt and source-ref body
      checks keep their gap codes and the golden data passes.
- [ ] 4.3 Retarget the lease and handoff tests. Done when the 12 rows and 6 destructive rows leave.
- [ ] 4.4 Record S4 deltas. Done when product (+20) and test (-80) deltas are written, and the test
      total is on course for the gate or the work is returned to the committee.

## 5. S5: removal, provider and documents

- [ ] 5.1 Delete the old command modules, `_COMMAND_MODULES`, `load_command_groups`, the admission
      tables and the classifier fallback. Done when no `lane`, `hook` or `attestation` module
      remains under `surface/cli/` and `ethos_step_*` are gone.
- [ ] 5.2 Move the docs-registry provider as its own commit. Done when the docs-registry gate passes
      and the five importing tests use the exported constant.
- [ ] 5.3 Update the command-plane spec, `rules/module-layout.md`, `docs/reference/command-plane.md`
      and `CHANGELOG.md`. Done when the docs gates pass and the CHANGELOG names every refusal.
- [ ] 5.4 Record S5 deltas. Done when product (-50) and test (-30) deltas are written.

## 6. Acceptance

- [ ] 6.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head and `lint-imports` shows the 52 rows gone.
- [ ] 6.2 Check the budget. Done when the Change totals at most +200 product and at most -100 test
      effective lines, and 12 destructive rows are gone.
