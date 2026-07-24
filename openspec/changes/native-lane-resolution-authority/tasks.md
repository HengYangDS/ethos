## 1. Refresh-first successor authority carrier

- [x] 1.1 Replay the approved planning carrier into the successor lane with
  signed provenance from the predecessor planning commit.
- [x] 1.2 Continue from a successor created at current `candidate/dev` after the
  native refresh of the stale implementation lane reported real conflicts.
- [x] 1.3 Preserve the clean predecessor lane as a read-only rollback carrier;
  product implementation will use semantic replay rather than bulk cherry-pick.
- [x] 1.4 Record that candidate staged-index recovery package v2 from `8fcea306d`
  is current truth and that predecessor preservation commit `21142430c` cannot be
  cherry-picked as a unit.
- [x] 1.5 Keep the predecessor Claim active and bind the new Claim only as
  implementation authorization until replacement implementation, proof, and
  official archive evidence support later supersession.
- [x] 1.6 Pass strict official OpenSpec and Claim validation for the revised
  design, plan, scope, Chronicle, and Claim boundary before product replay begins.

## 2. Provider-neutral contracts and record roots

- [ ] 2.1 Add RED tests for receipt version 3, reservation version 2, clear
  version 1, closed provider-neutral fields, canonical bytes, and exact 40/64
  lowercase Git OIDs.
- [ ] 2.2 Implement `ethos_core/contracts/resolution/closeout.py`, remove moved
  contracts from `lane.py`, update schemas, and keep package roots docstring-only.
- [ ] 2.3 Add RED tests for one versioned current root and explicit immutable
  historical roots with no current-to-history fallback.
- [ ] 2.4 Implement `current_record_root()` and `historical_record_roots()` and
  reconnect direct imports without compatibility aliases.

## 3. Strict current records, inventory, clear, and reservation persistence

- [ ] 3.1 Add RED tests for decision-only inventory, invalid current payloads,
  traversal/symlink cases, canonical snapshots, immutable reservation CAS, and
  competing reservations.
- [ ] 3.2 Implement concrete `records/current`, `records/clear`, and
  `records/reservations.py` owners; delete the ambiguous release helper.
- [ ] 3.3 Enumerate decisions, manifests, receipts, clears, and reservations;
  expose `decision_pending` and blocking invalid-current-record state.
- [ ] 3.4 Run focused record/receipt/clear tests, schemas, types, code-size,
  module-layout, and no-compat before independent review.

## 4. Descriptor-safe preservation on current recovery package v2

- [ ] 4.1 Add RED cases for non-UTF8 members, descriptor/path swaps, symlinks,
  unsupported members, bounded large-file capture, byte-mode Git failures, and
  staged plus unstaged recovery.
- [ ] 4.2 Port predecessor descriptor/no-follow/tarfile behavior semantically;
  do not cherry-pick `21142430c` and do not invoke external `tar`.
- [ ] 4.3 Retain `package_format_version=v2`, `tracked.patch`, `index.patch`,
  `patch_sha256`, `index_patch_sha256`, and candidate staged-index tests.
- [ ] 4.4 Pass focused preservation tests and prove the candidate v2 contract was
  not regressed.

## 5. Net-neutral layout correction and exact observation

- [ ] 5.1 Add RED layout regressions proving five-to-five rename is allowed,
  five-to-six growth remains blocked, and burst rules are unchanged.
- [ ] 5.2 Change existing-directory flat-growth reporting only when
  `current_count > previous_count`; do not alter limits or baselines.
- [ ] 5.3 Add RED observation cases for fixed byte-mode Git,
  `GIT_OPTIONAL_LOCKS=0`, malformed worktree output, hidden index flags, dirty
  state, descriptor/path swaps, and same-path/same-ref/same-HEAD recreation.
- [ ] 5.4 Replace `_observation.py` with public `observation.py` and implement
  `GitWorktreeRegistrationToken` from pinned worktree/gitfile/admin/backlink
  descriptors and exact bytes.
- [ ] 5.5 Add RED Chronicle cases for root-bound working bytes and exactly one
  accepted-tree regular blob mode (`100644` or `100755`); reject symlink,
  submodule, tree, duplicate, malformed, and failed observations.

## 6. Strict native admission and raw local-state validation

- [ ] 6.1 Add RED cases for exact decision/Chronicle facts, absence-only policy
  defaults, strict present-policy TOML/table/field types, custom
  `work_branch_prefix`, accepted ancestry, current-record integrity, lease/Claim/
  holder state, retry reservation, and competing reservation.
- [ ] 6.2 Validate raw SQLite row and JSON field types before holder parsing or
  strict model construction; damaged state and sidecars remain unverifiable.
- [ ] 6.3 Implement frozen fact-only `OwnerlessCloseoutAdmission`,
  `admit_ownerless_closeout(*, root, decision_path, decision, executor_ref)`,
  and `reobserve_ownerless_closeout_under_fence(*, admission, fence)` without
  callable/runtime fields.
- [ ] 6.4 Run the after-fence probe from a `finally` boundary for every exception
  and require exact before/after fence equality.
- [ ] 6.5 Keep admission within the logic soft limit and pass focused state,
  admission, fence, Ruff, types, schemas, code-size, and module-layout gates.

## 7. Effect, retry, recovery, and cleanup reconnection

- [ ] 7.1 Add RED tests for completed-effect recovery before target observation,
  same-head and descendant zero-effect retry, divergence, drift, crash windows,
  three-state probes, removal failure, receipt-present cleanup, and post-CAS
  exceptions.
- [ ] 7.2 Enforce the order: recovery precheck, exact pre-fence native admission
  and reservation classification, release/reset of the old exact zero-effect
  fence and reservation when classified, fresh fence acquisition, complete
  under-fence re-observation, typed reservation, no-force removal, accepted-ref
  verification, exact target-ref CAS, postconditions, receipt, fence-CAS release,
  reservation removal.
- [ ] 7.3 Delete `OwnerlessCloseoutRuntime`, `ResolutionRuntime`,
  `_ownerless_runtime()`, `_resolution_runtime()`, callback dictionaries, and the
  retired external adapter package/test.
- [ ] 7.4 Replace `fence_acquired: bool` with explicit phase/recovery state and
  preserve visible partial/unknown transitions at or after effect.
- [ ] 7.5 Pass the complete effect/retry/recovery/crash/cleanup/three-state suite,
  import linter, and no-compat gate.

## 8. Declaration-driven mandatory executable coupling

- [ ] 8.1 Expand active Change scope to the exact coupling contract, audit,
  schema, and test paths before writing them.
- [ ] 8.2 Add RED fixtures for undeclared executables, dynamic `argv[0]`, command
  strings, `shell=True`, executable override, path escape, literal declared Git,
  and optional adapters outside mandatory paths.
- [ ] 8.3 Declare audit-root-bound mandatory lane-resolution paths and only literal
  `git` as their external executable in `system/coupling.toml`.
- [ ] 8.4 Implement the generic AST audit and report/schema projection without a
  provider-name blacklist or whole-repository subprocess scan.
- [ ] 8.5 Pass coupling, schema, config, and product-boundary gates while preserving
  optional semantic-attestation/control-replacement behavior.

## 9. Current tracked truth convergence

- [ ] 9.1 Enumerate every current tracked WCP text/path match and delete the
  retired adapter and provider-response test.
- [ ] 9.2 Normalize source, tests, schemas, canonical specs, command reference,
  active plans, Claims, Chronicle, and archived OpenSpec wording while preserving
  dates, decisions, actions, evidence digests, limitations, and chronology.
- [ ] 9.3 Remove the literal token from this active Change before final scan;
  prevention remains generic through closed contracts and executable coupling.
- [ ] 9.4 Recompute only stale tracked evidence digests and pass Claim/OpenSpec
  validation.
- [ ] 9.5 Prove both tracked content search and tracked filename search return no
  WCP result without rewriting Git history or local predecessor records.

## 10. Branch-owned quality debt and independent review

- [ ] 10.1 Remove branch-owned `EM101`, `TRY003`, and `PLR0911` findings without
  expanding `.config/checks/ruff/ratchet.toml`.
- [ ] 10.2 Split the oversized lane-resolution record edge test into a two-module
  semantic subpackage; do not raise code-size or module-layout limits.
- [ ] 10.3 Pass focused tests, Ruff, types, schemas, code-size, module-layout,
  no-compat, and import gates.
- [ ] 10.4 Complete independent reviews for contracts/records, preservation,
  observation/admission, effect/recovery, coupling, and truth convergence; resolve
  every Important or Critical finding in focused signed commits.

## 11. Full proof and official archive

- [ ] 11.1 Run all focused and full tests, coverage, lint, config, shell,
  Markdown, format, types, schemas, module-layout, code-size, no-compat, import,
  coupling, Claim, docs, OpenSpec, residue, and diff gates on one stable HEAD.
- [ ] 11.2 Execute generic shadow parity in the admitted successor, commit the
  evidence, and run exact-HEAD `ethos prove --execute` with no required gaps.
- [ ] 11.3 Check only tasks backed by fresh evidence, update Claim/Chronicle
  digests, and rerun exact-HEAD proof after that commit.
- [ ] 11.4 Officially archive the Change, update the Claim carrier, validate all
  specs, and rerun Claim, report, residue, and archive-HEAD executed proof.

## 12. Final refresh, land, accepted closeout, and housekeeping

- [ ] 12.1 Run native refresh immediately before land; if HEAD changes, rerun the
  complete proof bundle; if refresh conflicts, stop without hand-resolving the
  proven HEAD.
- [ ] 12.2 Land the exact proven HEAD to candidate and perform audited accepted-
  root closeout as a separate transition.
- [ ] 12.3 Report local publish readiness without remote push.
- [ ] 12.4 Retire only the exactly absorbed successor and task-owned predecessor
  mistake lanes through native landed retirement or Chronicle-bound
  preserve-retire when absorption cannot be proved.
- [ ] 12.5 Remove only task scratch, review packets, bytecode, caches, and temporary
  proof output; leave foreign lanes, virtual environments, Git history, local
  records, SQLite history, and session metadata untouched.
- [ ] 12.6 Finish with clean accepted/candidate roots, no live task-owned lease or
  registered task worktree, and truthful separate reports for land, accepted
  closeout, and local publish readiness.
