# Tasks

## 1. S1: catalog machinery, attestation and host run

- [x] 1.1 Spike the two unspiked cases in owned scratch. Done when the `process` exit and
      `lane prewrite --patch -` stdin both work through a generated signature, with the five earlier
      spike cases re-run on the real adapter.
- [x] 1.2 Generate the golden `next` data with the uncommitted generator. Done when one JSON file
      under `tests/fixtures/` holds `(argv, effects, authorization, destructive, exit kind)` for
      every leaf and its mode-bearing flag subsets, and the test docstring records its provenance.
- [x] 1.3 Complete the attestation and `host run` audit rows. Done when each ignored or checked flag
      has its exit before and after in the design's audit, with the product callers searched.
- [x] 1.4 Add path keys, `GROUPS`, `modes()`, the field types S1 uses and the `process` exit kind.
      Done when `select_argv` selects a three-word path with positionals and `--`, and the table
      test passes over every path.
- [x] 1.5 Build the generic group adapter and the full-path usage refusal. Done when the
      `(argv, command, exit)` table and the missing-required-field test pass for every migrated
      path.
- [x] 1.6 Convert `attestation` and `host run` to entries. Done when their CLI tests pass through
      the adapter, `host run` exits with its child's status, and the 5 rows and 1 destructive row
      leave.
- [x] 1.7 Fence part 1 and its test. Done when the listed S1 prefixes are in
      `src/ethos/adapters/admission/control/replacement.py` and the prefix test passes.
- [ ] 1.8 Record S1 deltas. Done when the measured kernel import cost, product delta (at most +110)
      and test delta (at most +100) are written in this task and the owner's fence acknowledgement
      is named. Measured on `ff8de8f41`: product +122 LE (`python_product` +142, 77,618), tests
      +102 LE (`python_tests` +142, 100,075, over the 100,000 terminal ceiling); kernel import
      +1.7 ms of about 215 ms; fence widening acknowledged by 97f828 on 2026-11-09. Open: both
      figures; the unplanned reference-closure owners cost +15 product LE.

## 2. S2: hook

- [x] 2.1 Add the `hook` audit rows. Done when every hook flag combination that changes from ignored
      to refused is listed with its product callers. The design's Audit holds the `hook` table from
      one probe of 62 argv shapes on both trees, and the CHANGELOG has one Breaking line per
      refusal.
- [x] 2.2 Convert the 7 `hook` leaves to entries with `A/hook/` halves. Done when `S/hook/` is gone,
      `hook commit-range --check peer-identity` selects, and the golden data passes for the group.
      `K/hook.py` declares 10 operations, run by `A/hook/{admission,installation}.py` and
      `A/retention.py:retire_records`; the golden test passes all 31 hook rows, 5 listed as refused.
- [x] 2.3 Retarget the hook tests and the fence. Done when the 14 rows and 3 destructive rows leave,
      `test_activation.py` passes, and the hook and retention prefixes are fenced. `lint-imports`
      keeps 4 contracts with 35 surface ignores (49 before), `_DESTRUCTIVE` has 8 rows (11 before),
      `tests/unit/adapters/repo/hook` passes (302), and the fence holds `A/hook/`, `retention.py`
      and `peer_identity.py` instead of `S/hook/`.
- [x] 2.4 Record S2 deltas. Done when product (+10) and test (-60) deltas are written. Measured
      against `d11cd9854`: product +4 LE (`python_product` +18, 77,636), tests -83 LE
      (`python_tests` -73, 100,002, still 2 over the 100,000 terminal ceiling at this base).

## 3. S3: lane lifecycle and repair

- [x] 3.1 Add the audit rows for the 13 leaves. Done when each is listed with its callers. The
      design's Audit holds the S3 table from one probe of 139 argv shapes on both trees and 13
      real previews against an invalid profile, and the CHANGELOG has one Breaking line per
      refusal.
- [x] 3.2 Convert `lane` status, housekeeping, candidate, prewrite, start, refresh-base,
      archive-change, project, format, repair-paradigm, trust-commit-signer, repair-signature and
      redact. Done when `--paths X`, the `=` form and stdin work through the real CLI. `K/lane.py`
      and `K/lane_repair.py` declare 29 operations, run by `A/lane/{lifecycle,admission,repair}.py`
      through `A/lane/result.py`; the prewrite path-spelling test and the redaction tests pass
      through the CLI, which reads stdin for the operation.
- [x] 3.3 Retarget the lane tests, the fence and the import-set test. Done when the 18 rows and 2
      destructive rows leave and `lane prewrite` builds no other group's application half or App.
      `lint-imports` keeps 4 contracts with 17 surface ignores (35 before), `_DESTRUCTIVE` has 6
      rows (8 before), the fence holds `A/lane/` and `redaction.py`, and the import-set test passes:
      a `lane prewrite` process imports only the `A/lane` admission half among the implementations
      and builds only the `lane` App with its 13 catalog commands (242 ETHOS modules, 345 before).
- [x] 3.4 Record S3 deltas and the `lane prewrite` start-time measurement. Done when product (+50)
      and test (-80) deltas are written. Measured against `d3902d1bc`: product +46 LE
      (`python_product` +86, 77,749), tests -93 LE (`python_tests` -23, 99,888). `lane prewrite`,
      31 interleaved runs per tree at load 22 to 29: import, registration, parse and half import
      median 1,374 ms before and 1,153 ms after; the whole command 2,465 ms and 2,211 ms.

## 4. S4: lane retire, handoff, lease

- [x] 4.1 Add the audit rows for the 13 leaves. Done when each is listed with its callers. The
      design's Audit holds the S4 table from one probe of 106 argv shapes on both trees and 13 real
      previews against an invalid profile, and the CHANGELOG has one Breaking line per refusal.
- [x] 4.2 Convert `lane retire`, `handoff` and `lease`. Done when the receipt and source-ref body
      checks keep their gap codes and the golden data passes. `K/retire.py`, `K/lease.py` and
      `K/handoff.py` declare 28 operations, run by `A/lane/{retirement,lease}.py` through
      `A/lane/result.py`; `lane retire abandon --apply` without `--receipt` keeps
      `lane_retirement_receipt_required` and `lane refresh-base --source-ref` keeps
      `merge_source_ref_requires_merge_strategy` on both trees, and the golden test passes all 215
      rows, 58 marked refused.
- [x] 4.3 Retarget the lease and handoff tests. Done when the 12 rows and 6 destructive rows leave.
      `lint-imports` keeps 4 contracts with 5 surface ignores (17 before), `_DESTRUCTIVE` and
      `ethos_step_destructive` are gone (6 rows before), `S/lane/` is deleted, and
      `tests/unit/cli/test_lease_commands.py` runs the Lease and handoff halves through `invoke`
      in place of `test_lane_handoff.py`.
- [x] 4.4 Record S4 deltas. Done when product (+20) and test (-80) deltas are written, and the test
      total is on course for the gate or the work is returned to the committee. Measured against
      `0ab830dfa`: product +17 LE (`python_product` -2, 77,747), tests -153 LE (`python_tests`
      -73, 99,854). Measuring the slice commits directly puts the Change at +206 product LE
      before S5 (S2 measures +21 against its report's +4).

## 5. S5: removal, provider and documents

- [x] 5.1 Delete the old command modules, `_COMMAND_MODULES`, `load_command_groups`, the admission
      tables and the classifier fallback. Done when no `lane`, `hook` or `attestation` module
      remains under `surface/cli/` and `ethos_step_*` are gone. `surface/cli/` holds the adapter,
      its output and the `mcp` launcher, which the adapter loads for its own word or none;
      `run_application` builds the invoked word's commands; `next` reads every argv through the
      catalog alone, an unselected one `opaque`, destructive and `human`; and the S3 analyzer rule
      and its fixture leave, semantic closure and product boundaries passing without them.
- [x] 5.2 Move the docs-registry provider as its own commit. Done when the docs-registry gate passes
      and the five importing tests use the exported constant. `A/docs_registry.py` checks each
      example against the catalog's command and group paths and the `mcp` launcher, and
      `system/gates.toml` and the fence name it; the 3 `surface.cli.root.reference` rows leave (2
      surface ignores remain), and the docs-registry, markdown-links and prose gates pass on this
      commit's tree. The five tests take the provider from `A/docs_registry.py`;
      `test_host_gate_proof.py` patches it through the exported `DOCS_REGISTRY_PROVIDER`.
- [x] 5.3 Update the command-plane spec, `rules/module-layout.md`, `docs/reference/command-plane.md`
      and `CHANGELOG.md`. Done when the docs gates pass and the CHANGELOG names every refusal.
      Each MODIFIED requirement keeps every base scenario; a group's `--help --json` lists its own
      commands and its nested groups by name, so `lane` prints 43,021 bytes within the unchanged
      help budget (Decision 2); the CHANGELOG adds the provider, `next` and help lines; and the
      docs-registry, markdown-links and prose gates pass.
- [x] 5.4 Record S5 deltas. Done when product (-50) and test (-30) deltas are written. Measured
      against `a8f8c3b65`: product -44 LE (`python_product` -68, 77,679), tests -12 LE
      (`python_tests` -3, 99,851), the provider commit +3 and -1 LE of them; short of both figures,
      as S2 to S4 already retired the tests of the old modules.

## 6. Acceptance

- [ ] 6.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head and `lint-imports` shows the 52 rows gone.
- [ ] 6.2 Check the budget. Done when the Change totals at most +200 product and at most -100 test
      effective lines, and 12 destructive rows are gone. Measured against `2b113c640` on the S5
      tree: product +162 LE (`python_product` +197, 77,482 to 77,679), tests -239 LE
      (`python_tests` -30, 99,881 to 99,851), 52 of 54 surface ignore rows and the 12 destructive
      rows gone. The figures are effective lines, the unit the design states; the enforced token
      measure is product +197 and tests -30.
