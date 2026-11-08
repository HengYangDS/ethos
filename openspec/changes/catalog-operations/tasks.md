# Tasks

## 1. One implementation per operation

- [ ] 1.1 Map every operation to one implementation. Done when `IMPLEMENTATIONS` holds the 29 IDs,
      each a `(root, <its command's model>)` function under `ethos.application`, every SDK function
      only returns `invoke(...)`, and the table, signature and refused-mode tests pass.
- [ ] 1.2 Keep the transports alike. Done when the catalog, proof, CLI parity, publication effect
      and MCP binding tests pass on the committed head.

## 2. Console and projection

- [ ] 2.1 Move the console and the result projection. Done when `ethos.application.console` and
      `ethos.application.result_projection` hold the moved code, `surface/runtime_identity.py` is
      gone, the `resolve_root` importers and the listed patches are retargeted, and the console,
      output, version, runtime and process tests pass.
- [ ] 2.2 Retire the fifteen rows. Done when the import-linter configuration has none of them and
      its contracts are kept.

## 3. Acceptance

- [ ] 3.1 Pass the precheck and readiness at the lane head. Done when each passes on the committed
      head.
