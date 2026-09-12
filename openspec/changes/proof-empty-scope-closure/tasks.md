## 1. Bound the proof-plan behavior

- [x] 1.1 Add a RED proof-plan binding test for an empty current scope with valid historic archive authority; verify it fails because `openspec_archive` is forwarded and `proof_archive_scope_stale` is present.
- [x] 1.2 Add a non-empty current-scope counterpart assertion that preserves strict archive-path validation; verify it passes before the repair.
- [x] 1.3 Gate archive-authority forwarding in `proof_plan()` on the effective current path tuple; verify the focused proof-plan test passes.

## 2. Verify governed delivery

- [x] 2.1 Run the focused proof-plan binding suite and strict OpenSpec validation; verify both pass.
- [x] 2.2 Run lane-local `ethos prove --execute --full --expect-head <HEAD> --json`; record its current blocking verdict (`gate_failed:unit-architecture` and dependent gates) and make no land decision.
