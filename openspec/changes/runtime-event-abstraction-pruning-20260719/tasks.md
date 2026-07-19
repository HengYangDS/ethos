## 1. Direct lifecycle ownership

- [ ] 1.1 Replace lane CLI facade calls with direct lifecycle-owner calls.
- [ ] 1.2 Delete Runtime composition factories, forwarding functions, and the duplicate lease reader.
- [ ] 1.3 Migrate focused tests without compatibility aliases or wrappers.

## 2. Event abstraction pruning

- [ ] 2.1 Delete unused SQLite event and chronicle-event tables and CRUD surfaces.
- [ ] 2.2 Delete declaration-only workflow event models, TOML entries, schema fields, validation, counts, and self-proving tests.
- [ ] 2.3 Preserve Chronicle evidence and pure projection semantics explicitly.

## 3. Verification and local closeout

- [ ] 3.1 Run focused Ruff, type, architecture, state, workflow, and lane lifecycle tests.
- [ ] 3.2 Run Ponytail and broad code review; resolve all warnings and findings.
- [ ] 3.3 Refresh parity/claims if required, run HEAD-bound proof, land, accepted closeout, and retire the lane without remote push.
