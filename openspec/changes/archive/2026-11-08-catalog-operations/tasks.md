# Tasks

## 1. One implementation per operation

- [x] 1.1 Map every operation to one implementation. Done when `IMPLEMENTATIONS` holds the 29 IDs,
      each a `(root, <its command's model>)` function under `ethos.application`, every SDK function
      only returns `invoke(...)`, and the table, signature and refused-mode tests pass. Evidence: at
      bf0943ec7 `IMPLEMENTATIONS` maps the 29 operation IDs and every SDK function only returns
      `invoke(...)`; `test_each_operation_maps_to_one_implementation_of_its_command`,
      `test_each_root_operation_keeps_its_request_signature` and the `refused-mode-mapping` case of
      `test_the_operation_returns_what_the_command_renders` pass in the impacted sweep at 20980ad92
      (312 files: 5,719 passed and 2 skipped, 06:11:32 to 06:35:47).
- [x] 1.2 Keep the transports alike. Done when the catalog, proof, CLI parity, publication effect
      and MCP binding tests pass on the committed head. Evidence: `test_operation_catalog.py`,
      `test_proof_operation.py`, `test_catalog_commands.py`, `cli/land/publication/test_effect.py`
      and `surface/mcp/test_binding.py` pass in the impacted sweep at 20980ad92 (312 files: 5,719
      passed and 2 skipped, 06:11:32 to 06:35:47).

## 2. Console and projection

- [x] 2.1 Move the console and the result projection. Done when `ethos.application.console` and
      `ethos.application.result_projection` hold the moved code, `surface/runtime_identity.py` is
      gone, the `resolve_root` importers and the listed patches are retargeted, and the console,
      output, version, runtime and process tests pass. Evidence: at 45528d1e8
      `ethos.application.console` and `ethos.application.result_projection` hold the moved code,
      `surface/runtime_identity.py` is deleted and the 14 `resolve_root` importers are retargeted;
      `test_outcome_boundaries.py`, `test_invalid_profile_boundary.py`, `test_invocation_facts.py`,
      `surface/cli/test_output.py`, `test_version_command.py` and `test_result_runtime.py` pass in
      the impacted sweep at 20980ad92 (312 files: 5,719 passed and 2 skipped, 06:11:32 to 06:35:47).
- [x] 2.2 Retire the fifteen rows. Done when the import-linter configuration has none of them and
      its contracts are kept. Evidence: 45528d1e8 removes the 15 rows from
      `.config/checks/import-linter/import-linter.toml`; at 20980ad92 `lint-imports` keeps 4
      contracts and breaks none (06:23:20 to 06:23:21).

## 3. Acceptance

- [x] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head. Evidence: at 20980ad92 the static precheck passed with no finding over 56 changed files
      (06:22:58 to 06:23:01), readiness passed 28 gates (06:13:22 to 06:14:48), the impacted sweep
      passed (312 files: 5,719 passed and 2 skipped, 06:11:32 to 06:35:47) and the host gate
      `local-install-smoke` passed (06:36:08 to 06:46:38).
