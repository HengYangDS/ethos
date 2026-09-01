## 1. Intent and regression

- [x] 1.1 Define clean changed-scope behavior in the `command-plane` delta and
  verify `openspec validate clean-changed-plan-closure --strict` passes.
- [x] 1.2 Add a public command regression that fails on the current
  `proof_archive_scope_stale` result while preserving non-empty archive-scope
  rejection tests.

## 2. Implementation

- [x] 2.1 Terminate `plan --changed` as a successful no-op when fresh changed
  paths are empty, without resolving historical OpenSpec intent.
- [x] 2.2 Delete any now-redundant empty-scope path and verify no compatibility
  branch or duplicate owner remains.

## 3. Closure

- [x] 3.1 Run focused command, resolver, and proof-plan tests plus Ruff and
  repository-wide reference checks.
- [x] 3.2 Update the existing terminal design plan with the closed gap and
  remaining successor order.
- [ ] 3.3 Complete signed exact-HEAD proof, official archive/reproof,
  candidate/accepted CAS, runtime readback, and Work Lane retirement.
