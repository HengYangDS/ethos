## 1. Direct lifecycle ownership

- [x] 1.1 Replace lane CLI facade calls with direct lifecycle-owner calls.
- [x] 1.2 Delete Runtime composition factories, forwarding functions, and the duplicate lease reader.
- [x] 1.3 Migrate focused tests without compatibility aliases or wrappers.
- [x] 1.4 Delete every Runtime dependency container and runtime parameter.

## 2. Event abstraction pruning

- [x] 2.1 Delete unused SQLite event and chronicle-event tables and CRUD surfaces.
- [x] 2.2 Delete declaration-only workflow event models, TOML entries, schema fields, validation, counts, and self-proving tests.
- [x] 2.3 Preserve Chronicle evidence and pure projection semantics explicitly.
- [x] 2.4 Delete local SQLite schema migration and retired-format compatibility.
- [x] 2.5 Delete standards-adapter records without production implementations.

## 3. Verification and local closeout

- [x] 3.1 Run focused Ruff, type, architecture, state, workflow, and lane lifecycle tests.
- [x] 3.2 Run Ponytail and broad code review; resolve all warnings and findings.
- [ ] 3.3 Refresh parity/claims if required, run HEAD-bound proof, land, accepted closeout, and retire the lane without remote push.
