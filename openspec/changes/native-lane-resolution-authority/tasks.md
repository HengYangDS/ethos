
> **Closure evidence correction — 2026-07-26.** The historical TDD ordering was not retained as a contemporaneous command/exit receipt. For tasks 2.1, 2.3, 3.1, 4.1, 5.1, 5.3, 5.5, 6.1, 7.1, and 8.2, a checked box therefore means a current disposable-copy mutant replay produced RED and the unmodified tree produced GREEN; it does **not** retroactively certify the original implementation order. Tasks 8.1, 9.2, and 9.4 are likewise closed only to their current evidence-bound meanings: final declared-scope validation, bounded current-surface normalization with history preserved, and current Claim/OpenSpec validation. Archive, canonical fusion, Claim supersession, and terminal WCP removal remain post-checklist transitions.

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

- [x] 2.1 Add RED tests for receipt version 3, reservation version 2, clear
  version 1, closed provider-neutral fields, canonical bytes, and exact 40/64
  lowercase Git OIDs.
- [x] 2.2 Implement `ethos_core/contracts/resolution/closeout.py`, remove moved
  contracts from `lane.py`, update schemas, and keep package roots docstring-only.
- [x] 2.3 Add RED tests for one versioned current root and explicit immutable
  historical roots with no current-to-history fallback.
- [x] 2.4 Implement `current_record_root()` and `historical_record_roots()` and
  reconnect direct imports without compatibility aliases.

## 3. Strict current records, inventory, clear, and reservation persistence

- [x] 3.1 Add RED tests for decision-only inventory, invalid current payloads,
  traversal/symlink cases, canonical snapshots, immutable reservation CAS, and
  competing reservations.
- [x] 3.2 Implement concrete `records/current`, `records/clear`, and
  `records/reservations.py` owners; delete the ambiguous release helper.
- [x] 3.3 Enumerate decisions, manifests, receipts, clears, and reservations;
  expose `decision_pending` and blocking invalid-current-record state.
- [x] 3.4 Run focused record/receipt/clear tests, schemas, types, code-size,
  module-layout, and no-compat before independent review.

## 4. Descriptor-safe preservation on current recovery package v2

- [x] 4.1 Add RED cases for non-UTF8 members, descriptor/path swaps, symlinks,
  unsupported members, bounded large-file capture, byte-mode Git failures, and
  staged plus unstaged recovery.
- [x] 4.2 Port predecessor descriptor/no-follow/tarfile behavior semantically;
  do not cherry-pick `21142430c` and do not invoke external `tar`.
- [x] 4.3 Retain `package_format_version=v2`, `tracked.patch`, `index.patch`,
  `patch_sha256`, `index_patch_sha256`, and candidate staged-index tests.
- [x] 4.4 Pass focused preservation tests and prove the candidate v2 contract was
  not regressed.

## 5. Net-neutral layout correction and exact observation

- [x] 5.1 Add RED layout regressions proving five-to-five rename is allowed,
  five-to-six growth remains blocked, and burst rules are unchanged.
- [x] 5.2 Change existing-directory flat-growth reporting only when
  `current_count > previous_count`; do not alter limits or baselines.
- [x] 5.3 Add RED observation cases for fixed byte-mode Git,
  `GIT_OPTIONAL_LOCKS=0`, malformed worktree output, hidden index flags, dirty
  state, descriptor/path swaps, and same-path/same-ref/same-HEAD recreation.
- [x] 5.4 Replace `_observation.py` with public `observation.py` and implement
  `GitWorktreeRegistrationToken` from pinned worktree/gitfile/admin/backlink
  descriptors and exact bytes.
- [x] 5.5 Add RED Chronicle cases for root-bound working bytes and exactly one
  accepted-tree regular blob mode (`100644` or `100755`); reject symlink,
  submodule, tree, duplicate, malformed, and failed observations.

## 6. Strict native admission and raw local-state validation

- [x] 6.1 Add RED cases for exact decision/Chronicle facts, absence-only policy
  defaults, strict present-policy TOML/table/field types, custom
  `work_branch_prefix`, accepted ancestry, current-record integrity, lease/Claim/
  holder state, retry reservation, and competing reservation.
- [x] 6.2 Validate raw SQLite row and JSON field types before holder parsing or
  strict model construction; damaged state and sidecars remain unverifiable.
- [x] 6.3 Implement frozen fact-only `OwnerlessCloseoutAdmission`,
  `admit_ownerless_closeout(*, root, decision_path, decision, executor_ref)`,
  and `reobserve_ownerless_closeout_under_fence(*, admission, fence)` without
  callable/runtime fields.
- [x] 6.4 Run the after-fence probe from a `finally` boundary for every exception
  and require exact before/after fence equality.
- [x] 6.5 Keep admission within the logic soft limit and pass focused state,
  admission, fence, Ruff, types, schemas, code-size, and module-layout gates.

## 7. Effect, retry, recovery, and cleanup reconnection

- [x] 7.1 Add RED tests for completed-effect recovery before target observation,
  same-head and descendant zero-effect retry, divergence, drift, crash windows,
  three-state probes, removal failure, receipt-present cleanup, and post-CAS
  exceptions.
- [x] 7.2 Enforce the order: recovery precheck, exact pre-fence native admission
  and reservation classification, release/reset of the old exact zero-effect
  fence and reservation when classified, fresh fence acquisition, complete
  under-fence re-observation, typed reservation, no-force removal, accepted-ref
  verification, exact target-ref CAS, postconditions, receipt, fence-CAS release,
  reservation removal.
- [x] 7.3 Delete `OwnerlessCloseoutRuntime`, `ResolutionRuntime`,
  `_ownerless_runtime()`, `_resolution_runtime()`, callback dictionaries, and the
  retired external adapter package/test.
- [x] 7.4 Replace `fence_acquired: bool` with explicit phase/recovery state and
  preserve visible partial/unknown transitions at or after effect.
- [x] 7.5 Pass the complete effect/retry/recovery/crash/cleanup/three-state suite,
  import linter, and no-compat gate.

## 8. Declaration-driven mandatory executable coupling

- [x] 8.1 Expand active Change scope to the exact coupling contract, audit,
  schema, and test paths before writing them.
- [x] 8.2 Add RED fixtures for undeclared executables, dynamic `argv[0]`, command
  strings, `shell=True`, executable override, path escape, literal declared Git,
  and optional adapters outside mandatory paths.
- [x] 8.3 Declare audit-root-bound mandatory lane-resolution paths and only literal
  `git` as their external executable in `system/coupling.toml`.
- [x] 8.4 Implement the generic AST audit and report/schema projection without a
  provider-name blacklist or whole-repository subprocess scan.
- [x] 8.5 Pass coupling, schema, config, and product-boundary gates while preserving
  optional semantic-attestation/control-replacement behavior.

## 9. Current tracked truth convergence

- [x] 9.1 Enumerate every current tracked retired-provider identifier
  text/path match and delete the retired adapter and provider-response test.
- [x] 9.2 Normalize source, tests, schemas, canonical specs, command reference,
  active plans, Claims, Chronicle, dated retention projections, and archived
  OpenSpec wording while preserving dates, decisions, actions, evidence digests,
  limitations, original-object provenance, and chronology.
- [x] 9.3 Remove the literal token from this active Change before final scan;
  prevention remains generic through closed contracts and executable coupling.
- [x] 9.4 Recompute only stale tracked evidence digests and pass Claim/OpenSpec
  validation.
- [x] 9.5 Prove both tracked content search and tracked filename search return no
  retired-provider identifier result without rewriting Git history or local
  predecessor records.

## 10. Branch-owned quality debt and independent review

- [x] 10.1 Remove branch-owned `EM101`, `TRY003`, and `PLR0911` findings without
  expanding `.config/checks/ruff/ratchet.toml`.
- [x] 10.2 Split the oversized lane-resolution preservation Git-payload test into
  a semantic sibling module; do not raise code-size or module-layout limits.
- [x] 10.3 Pass focused tests, Ruff, types, schemas, code-size, module-layout,
  no-compat, and import gates.
- [x] 10.4 Complete independent reviews for contracts/records, preservation,
  observation/admission, effect/recovery, coupling, and truth convergence; resolve
  every Important or Critical finding in focused signed commits.

## 11. Full proof and official archive

- [x] 11.1 Run all focused and full tests, coverage, lint, config, shell,
  Markdown, format, types, schemas, module-layout, code-size, no-compat, import,
  coupling, Claim, docs, OpenSpec, residue, and diff gates on one stable HEAD.
- [x] 11.2 Execute generic shadow parity in the admitted successor, commit the
  evidence, and close only checklist items backed by fresh gate/parity evidence.
- [ ] 11.3 After every implementation and parity input is committed, execute the
  final exact-HEAD pre-archive proof, confirm isolated archive preflight is ready,
  and close this checklist in an evidence-only commit. This item does not claim a
  second self-referential proof for the checklist-only commit.

## Post-archive transition boundary

The following are audited transitions after this checklist is complete. They are
not pre-archive tasks and MUST NOT be checked or claimed before their own
receipts exist:

- officially archive the Change, use the dated path returned by OpenSpec,
  migrate the native Claim carrier, supersede the predecessor Claim, validate
  all specs, and execute proof on the archive commit;
- refresh the archive-proven HEAD and land that exact HEAD to candidate;
- obtain a candidate-external one-shot control-replacement verifier receipt when
  required, then perform accepted-root closeout as a separate transition;
- report local publish readiness without remote push;
- retire the landed successor only through holder-bound landed retirement, and
  judge diverged predecessor mistake lanes one at a time through Chronicle-bound
  preserve-retire rather than invented absorption;
- remove only task scratch, review packets, bytecode, caches, and temporary
  proof output while leaving foreign lanes, virtual environments, Git history,
  historical records, SQLite state, and session metadata untouched.
