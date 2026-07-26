## 1. Exact boundary and RED evidence

- [x] 1.1 Bind the accepted baseline, no-effect failure, exact source boundary,
  and no-SQLite-mutation constraint in OpenSpec, Claim, and Chronicle carriers.
- [x] 1.2 Add RED coverage proving unrelated legacy rows do not block exact
  observation or fence acquisition.
- [x] 1.3 Add RED coverage proving malformed exact-target rows remain
  fail-closed and native admission plus fenced re-observation use the same rule.

## 2. Minimal implementation

- [x] 2.1 Replace whole-table lease validation in ownerless closeout with a
  bound exact-subject query and unchanged strict row validation.
- [x] 2.2 Pass the exact subject through read observation and transactional
  fence acquisition without changing error tokens or public APIs.
- [x] 2.3 Confirm no `__init__.py`, schema, maintenance, lifecycle, dependency,
  or unrelated source change entered the diff.

## 3. Proof and promotion

- [x] 3.1 Run focused RED-to-GREEN tests, changed-scope planning, strict
  OpenSpec/Claim/docs checks, and the required quality gates.
- [ ] 3.2 Archive through the official OpenSpec transition, refresh committed
  generic parity, and execute exact-HEAD proof.
- [ ] 3.3 Land to candidate, accepted-close to `dev` and `main`, then retire
  only this exact owned carrier with fresh evidence.

## 4. Post-acceptance boundary

- [ ] 4.1 Re-observe each exact missing-lease source and create new decisions;
  never reuse either the Chronicle-invalid or observation-stale decision.
- [ ] 4.2 Preserve accepted-ancestor no-effect results and require a separate
  accepted reconciliation before changing disposition to `preserve-retire`.
- [ ] 4.3 Keep valid-owner lanes, retained packages, legacy lease maintenance,
  remotes, broad caches, build evidence, virtual environments, and IDE/session
  state outside this Change.
