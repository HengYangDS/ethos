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
- [x] 3.2 Archive through the official OpenSpec transition and bind committed
  generic parity plus exact-HEAD proof as the promotion sequence.
- [x] 3.3 Bind candidate land, accepted-close to `dev` and `main`, and exact
  carrier retirement as post-proof transitions requiring fresh command
  evidence.

## 4. Post-acceptance boundary

- [x] 4.1 Require fresh re-observation and new decisions for both exact sources;
  never reuse either the Chronicle-invalid or observation-stale decision.
- [x] 4.2 Require accepted-ancestor no-effect results to remain visible and a
  separate accepted reconciliation before changing disposition to
  `preserve-retire`.
- [x] 4.3 Keep valid-owner lanes, retained packages, legacy lease maintenance,
  remotes, broad caches, build evidence, virtual environments, and IDE/session
  state outside this Change.
