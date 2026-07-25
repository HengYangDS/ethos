---
subject: ethos:native-lane-resolution-authority-implementation-plan-20260724
role: plan
state: active
relations:
  implements: native-lane-resolution-authority-design-20260724
---

# Native Lane Resolution Authority Implementation Plan

Status: active; successor carrier established, production replay not yet accepted.

Purpose: execute the approved native lane-resolution authority cut through
refresh-first semantic replay, test-first implementation, independent review,
proof, archive, land, accepted closeout, and bounded housekeeping.

See also: [Design](native-lane-resolution-authority-design-20260724.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Command Plane](../reference/command-plane.md).

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` task
> by task. Every production slice starts with an observed RED test and ends with
> a signed commit plus an independent Important/Critical review gate.

**Goal:** Make ETHOS the sole owner of Work Lane observation, admission, records,
effect, retry, recovery, and cleanup; remove retired-provider authority residue
from current tracked product truth without rewriting history or local predecessor
records.

**Architecture:** Continue from a successor Work Lane based on current
`candidate/dev`. Replay old-lane work by semantic slice, never by bulk production
cherry-pick. Use exact native observation and an immutable fact snapshot before
reusing the existing fence, reservation, no-force removal, exact ref CAS,
postcondition, receipt, and cleanup mechanisms.

**Tech stack:** Python 3.14, Pydantic strict models, JSON Schema 2020-12, SQLite,
fixed-literal Git plumbing, descriptor-relative POSIX file APIs, stdlib
`tarfile`, pytest, Ruff, ty, OpenSpec 1.6, and ETHOS lifecycle commands.

## Global constraints

- Work only in the owned successor root reported by `ethos status --json`
  unless native refresh fails again and a newly named successor is created from
  the current candidate. Examples below use `<successor-root>`,
  `<candidate-root>`, and `<accepted-root>` for live command-plane paths; never
  substitute a remembered workstation path.
- Export
  `ETHOS_ACTOR=agent:codex:thread:019f8f90-7bcb-7a11-8fd2-a953c8bbbc06`.
- Run every ETHOS command through `tools/ci/scripts/run-ethos-lane.sh`.
- Immediately before every tracked write, run fresh `status --json` and exact
  `lane prewrite` with `--editor-root` and `--require-editor-root`.
- Every commit is signed (`git commit -S`).
- Do not cherry-pick any production commit from the predecessor lane. `git show`
  may be used as a read-only reference after current candidate behavior is
  established by tests.
- Specifically, do not cherry-pick `21142430c`. Candidate commit `8fcea306d`
  owns recovery package v2 and staged-index preservation; `index.patch` and
  `index_patch_sha256` must survive every preservation change.
- Every `__init__.py` contains only a docstring. Import from defining modules;
  no facade, barrel, alias shim, `__getattr__`, compatibility fallback,
  single-implementation Protocol, runtime service bag, or callback dictionary.
- No tracked baseline expansion in Ruff, module-layout, code-size, import, or
  compatibility policy.
- No real foreign lane is mutated or retired during implementation acceptance.
- Do not rewrite Git history, predecessor local records, SQLite history,
  virtual environments, or IDE/session JSONL/database state.
- Remote push and hosted mutation are not authorized.

Before each task write, export the actor, run fresh status, then invoke
`tools/ci/scripts/run-ethos-lane.sh lane prewrite` with every exact create,
modify, and delete path in that task's **Files** list plus
`--editor-root "$(git rev-parse --show-toplevel)" --require-editor-root --json`.
Do not shorten that request with a directory wildcard. Repeat status and
prewrite after every commit because the lease binding HEAD has changed.

Stop the task if status is not a clean owned Work Lane, prewrite is not
`state=admitted`, the candidate is not an ancestor of `HEAD`, or an exact path is
outside the active OpenSpec scope.

## Task 1: Refresh-first successor baseline and rollback carrier

**OpenSpec alignment:** section 1.

**Read-only inputs:**

- `candidate/dev`
- `work/20260724-native-lane-resolution-authority`
- `work/20260724-native-lane-resolution-authority-successor`
- active Change `native-lane-resolution-authority`

**Produces:** a current successor baseline, a clean predecessor rollback carrier,
and explicit permission for semantic replay only.

1. Verify current identity and candidate ancestry:

   ```text
   tools/ci/scripts/run-ethos-lane.sh status --json
   tools/ci/scripts/run-ethos-lane.sh lane status --json
   git merge-base --is-ancestor candidate/dev HEAD
   git status --short --branch
   ```

   Expected: owned successor lane, clean worktree, and exit 0 from the ancestry
   check.

2. If candidate has advanced, run native refresh before any implementation:

   ```text
   tools/ci/scripts/run-ethos-lane.sh lane refresh-base \
     --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
   ```

   Expected: applied refresh and clean worktree. If the command reports a real
   conflict, confirm it aborted and restored the old HEAD, then stop this lane.

3. After a refresh conflict, create the next successor from the configured
   candidate root instead of resolving the stale lane in place:

   ```text
   cd <candidate-root>
   tools/ci/scripts/run-ethos-lane.sh lane start \
     20260724-native-lane-resolution-authority-successor-2 \
     --holder-ref "$ETHOS_ACTOR" \
     --claim-id native-lane-resolution-authority-20260724 \
     --apply --json
   ```

4. Keep the predecessor lane clean and registered. Do not retire it until Task 13
   proves successor absorption.

5. Keep `ownerless-closeout-effect-fence-20260722` active until the native
   replacement has implementation, full proof, and official archive evidence.
   The new Claim authorizes implementation and records future supersession only.

6. Validate the planning carrier before production work:

   ```text
   openspec status --change native-lane-resolution-authority --json
   openspec validate native-lane-resolution-authority --strict --json
   tools/ci/scripts/run-ethos-lane.sh openspec \
     --change native-lane-resolution-authority --lifecycle --json
   ```

**Stop conditions:** failed ancestry, refresh conflict without a clean abort,
dirty predecessor, missing Change, or strict OpenSpec failure.

## Task 2: Replay provider-neutral contracts and record roots

**OpenSpec alignment:** section 2.

**Files:**

- Create: `packages/ethos-core/src/ethos_core/contracts/resolution/closeout.py`
- Modify: `packages/ethos-core/src/ethos_core/contracts/resolution/lane.py`
- Modify: `system/schemas/kernel/lane-resolution-receipt.schema.json`
- Modify: `system/schemas/kernel/lane-resolution-clear-receipt.schema.json`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/roots.py`
- Test: `tests/unit/kernel/test_lane_resolution_contract.py`
- Test: `tests/unit/cli/test_contracts_lane_resolution.py`
- Test: `tests/unit/lanes/test_lane_resolution_artifacts.py`

**Interfaces:**

```text
OwnerlessCloseoutBinding(BaseModel)
LaneResolutionReceipt(BaseModel)
OwnerlessCloseoutReservation(BaseModel)
LaneResolutionClearReceipt(BaseModel)
current_record_root(root: Path) -> Path
historical_record_roots(root: Path) -> tuple[Path, ...]
```

1. Add failing tests for closed version-3 receipts, version-2 reservations,
   version-1 clear receipts, exact 40/64 lowercase Git OIDs, provider-prefixed
   field rejection, newline rejection, and non-hex rejection.
2. Add failing root tests proving current readers select only
   `recovery/lane-resolution-v2/` and explicit history lookup never feeds current
   decide/apply/recovery/clear behavior.
3. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/kernel/test_lane_resolution_contract.py \
     tests/unit/cli/test_contracts_lane_resolution.py \
     tests/unit/lanes/test_lane_resolution_artifacts.py
   ```

   Expected: failures identify missing strict closeout contracts and root APIs.

4. Implement the minimal closed models and roots. Move ownerless binding and
   receipt definitions out of `lane.py`; do not re-export them from either
   package root.
5. Run GREEN with the command above, then:

   ```text
   tools/ci/scripts/run-ethos-lane.sh quality schemas --json
   tools/ci/scripts/run-ethos-lane.sh quality types --json
   tools/ci/scripts/run-module-layout.sh
   tools/ci/scripts/run-no-compat.sh
   ```

6. Commit:

   ```text
   git commit -S -m 'refactor(resolution): define native closeout contracts'
   ```

**Review boundary:** contract/schema/root shape only; no inventory, reservation
persistence, effect, or retired-provider cleanup in this commit.

## Task 3: Replay strict current records, inventory, clear, and reservations

**OpenSpec alignment:** section 3.

**Files:**

- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/records/core.py`
- Create declaration-only:
  `packages/ethos/src/ethos/adapters/mutation/resolution/records/io/__init__.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/io/core.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/io/posix.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/records/roots.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/records/inventory.py`
- Delete: `packages/ethos/src/ethos/adapters/mutation/resolution/records/release.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/current/core.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/current/snapshot.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/current/validation/core.py`
- Create declaration-only package roots under `records/current/` and
  `records/current/validation/`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/clear/core.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/clear/quarantine.py`
- Create declaration-only `records/clear/__init__.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/records/reservations.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/receipts.py`
- Test: `tests/unit/coverage/test_lane_resolution_record_edges.py`
- Test: `tests/unit/coverage/test_lane_resolution_reservation_edges.py`
- Test: `tests/unit/lanes/test_lane_resolution_clear_quarantine.py`
- Test: `tests/unit/lanes/test_lane_resolution_current_enumeration.py`
- Test package: `tests/unit/lanes/resolution/record_roots/`
- Test: `tests/unit/lanes/resolution/record_roots/test_roots_and_bound_snapshots.py`
- Test: `tests/unit/lanes/resolution/record_roots/test_atomic_record_transactions.py`
- Create declaration-only: `tests/unit/lanes/resolution/__init__.py`
- Create test support owner: `tests/unit/lanes/resolution/records.py`
- Test: `tests/unit/lanes/retirement/test_ownerless_closeout_records.py`
- Test: `tests/unit/lanes/retirement/test_ownerless_closeout_receipt_edges.py`

Independent-review repairs may also modify the concrete effect/recovery owners
and their existing tests when required to preserve current-record exclusion:

- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/_shared.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/lane.py`
- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/receipt.py`
- Modify concrete modules under
  `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/`
- Modify existing lane-resolution and ownerless recovery/effect tests under
  `tests/unit/coverage/` and `tests/unit/lanes/retirement/`

**Interfaces:**

```text
validate_ownerless_closeout_reservation(payload: object) -> dict[str, object]
ownerless_closeout_reservation_path(
  root: Path, target: str, *, artifact_root: Path | None = None
) -> Path
reserve_ownerless_closeout_target(
  *, root: Path, reservation: dict[str, object],
  artifact_root: Path | None = None
) -> Path
transition_ownerless_closeout_reservation(
  *, root: Path, expected: dict[str, object], phase: str,
  recovery_state: str, postcondition_digest: str = "",
  artifact_root: Path | None = None
) -> dict[str, object]
read_ownerless_closeout_reservation(
  *, record_root: Path, path: Path
) -> dict[str, object]
release_ownerless_closeout_reservation(
  *, root: Path, expected: dict[str, object],
  artifact_root: Path | None = None
) -> None
ownerless_closeout_reservation_admission(
  *, root: Path, record_root: Path, decision_path: Path,
  decision_sha256: str, expected: OwnerlessCloseoutReservation
) -> OwnerlessCloseoutReservation | None
lane_resolution_inventory(*, root: Path) -> dict[str, object]
```

1. Add failing tests for the identifier union of decisions, manifests, receipts,
   clears, and reservations; `decision_pending`; blocking invalid current bytes;
   traversal-spelled paths; symlink swaps; canonical bytes; immutable reservation
   CAS; competing reservations; and closed provider-neutral reservation shape.
2. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/coverage/test_lane_resolution_record_edges.py \
     tests/unit/coverage/test_lane_resolution_reservation_edges.py \
     tests/unit/lanes/test_lane_resolution_clear_quarantine.py \
     tests/unit/lanes/test_lane_resolution_current_enumeration.py \
     tests/unit/lanes/resolution/record_roots/test_roots_and_bound_snapshots.py \
     tests/unit/lanes/resolution/record_roots/test_atomic_record_transactions.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_records.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_receipt_edges.py
   ```

3. Implement current-record snapshots, validation, clear/quarantine, and typed
   reservation persistence. Use descriptor-bound no-follow reads and writes;
   handwritten validation may enforce storage atomicity but must delegate record
   shape to `OwnerlessCloseoutReservation`. Bind concurrent ETHOS writers through
   one repository-owned namespace lock outside the mutable record tree, revalidate
   lexical descriptor identity before and after each operation, and move owned
   destructive cleanup through an unpredictable private transaction namespace.
   Do not claim protection from arbitrary non-cooperating same-user mutation of
   that private namespace; fail closed when its identity cannot be proved.
4. Run GREEN, schemas, types, code-size, module-layout, and no-compat.
5. Commit record isolation and reservation persistence as two signed commits so
   either review slice can be rejected independently:

   ```text
   git commit -S -m 'refactor(lanes): cut record authority to current root'
   git commit -S -m 'refactor(resolution): own native reservation persistence'
   ```

**Stop conditions:** a historical root affects current inventory/effect, invalid
current bytes are skipped, or reservation replacement is not exact CAS.

## Task 4: Port descriptor-safe preservation without regressing package v2

**OpenSpec alignment:** section 4.

**Files:**

- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/preservation/core.py`
- Create declaration-only:
  `packages/ethos/src/ethos/adapters/mutation/resolution/preservation/__init__.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/_effects.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/receipts.py`
- Modify: `tests/unit/lanes/test_lane_resolution.py`
- Create: `tests/unit/lanes/resolution/test_preservation.py`
- Modify: `tests/unit/coverage/test_lane_resolution_edges.py`

**Interfaces:**

```text
write_git_preservation_payloads(
    *, source: Path, bundle: Path, tracked_patch: Path,
    index_patch: Path, lane_ref: str
) -> None
write_untracked_archive(*, source: Path, archive: Path, inventory: list[bytes]) -> None
run_git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]
```

1. Treat candidate commit `8fcea306d` and its tests as current truth. Use
   `21142430c`, `53ca29ad4`, `9dbba7ada`, and `0b795ab24` only as read-only
   semantic references for native archive creation, descriptor binding, bounded
   spooling, and payload typing; do not cherry-pick any of them. Add RED cases for
   raw non-UTF8 member names, parent symlink swap, regular-file swap, large-file
   bounded-memory capture, unsupported members, Git byte failures, staged plus
   unstaged recovery, and tampered `index.patch`.
2. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/lanes/test_lane_resolution.py \
     tests/unit/lanes/resolution/test_preservation.py \
     tests/unit/coverage/test_lane_resolution_edges.py
   ```

3. Port only the descriptor/no-follow/tarfile/bounded-spool behavior from the
   predecessor. Keep fixed Git, package format v2, `tracked.patch`, `index.patch`,
   `patch_sha256`, and `index_patch_sha256`. Do not restore the predecessor
   three-file package shape and do not invoke external `tar`.
4. Run GREEN and verify the specific staged-index contract:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/lanes/test_lane_resolution.py::test_preserve_retire_keeps_exact_index_and_worktree_deltas \
     tests/unit/lanes/resolution/test_preservation.py \
     tests/unit/coverage/test_lane_resolution_edges.py
   tools/ci/scripts/run-python-lint.sh
   tools/ci/scripts/run-module-layout.sh
   ```

5. Compare candidate truth before committing:

   ```text
   git diff candidate/dev -- \
     packages/ethos/src/ethos/adapters/mutation/resolution/_effects.py \
     packages/ethos/src/ethos/adapters/mutation/resolution/receipts.py \
     tests/unit/lanes/test_lane_resolution.py
   ```

   Expected: descriptor hardening and external-`tar` removal are added; staged-
   index v2 behavior is not deleted.
6. Commit:

   ```text
   git commit -S -m 'refactor(resolution): preserve recovery packages natively'
   ```

**Stop conditions:** missing or altered `index.patch`, package version other than
v2 for new packages, unbounded whole-file memory, external `tar`, text-mode Git
patch capture, or whole-commit cherry-pick of `21142430c`.

## Task 5: Correct the net-neutral module-rename gate

**OpenSpec alignment:** section 5.1.

**Required skill:** `ethos-quality-gate-governance`.

**Files:**

- Modify: `packages/ethos/src/ethos/repository/policy/layout/growth/core.py`
- Modify: `tests/unit/policy/test_module_layout_growth_edges.py`

1. Add three focused regressions:
   - one module renamed inside an existing five-module directory, keeping the
     total at five, is allowed;
   - five modules growing to six remains blocked;
   - existing burst and new-directory burst results are unchanged.
2. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/policy/test_module_layout_growth_edges.py
   ```

3. Change only the existing-directory growth condition so a flat-growth finding
   requires `current_count > previous_count`. Do not alter limits, baselines,
   burst rules, or new-directory rules.
4. Run GREEN and the owner gate:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/policy/test_module_layout_growth_edges.py
   tools/ci/scripts/run-module-layout.sh
   ```

5. Commit:

   ```text
   git commit -S -m 'fix(layout): allow net-neutral module renames'
   ```

## Task 6: Build exact Git, Chronicle, and registration observation

**OpenSpec alignment:** section 5.2.

**Files:**

- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/observation.py`
- Delete: `packages/ethos/src/ethos/adapters/mutation/resolution/_observation.py`
- Modify direct imports in `packages/ethos/src/ethos/adapters/mutation/resolution/lane.py`
  and `packages/ethos/src/ethos/adapters/mutation/resolution/_effects.py`
- Create declaration-only:
  `tests/unit/lanes/retirement/admission/__init__.py`
- Create: `tests/unit/lanes/retirement/admission/test_git_observation.py`
- Create: `tests/unit/lanes/retirement/admission/test_chronicle_observation.py`
- Modify: `tests/unit/lanes/retirement/test_ownerless_closeout_admission.py`
- Modify: `tests/unit/coverage/test_lane_resolution_edges.py`
- Modify: `tests/unit/lanes/retirement/test_ownerless_closeout_effect.py`
- Modify: `tests/unit/lanes/retirement/test_ownerless_closeout_cas_final_edges.py`

**Interfaces and immutable fields:**

```text
DescriptorIdentity(device, inode, mode, size, mtime_ns, ctime_ns)
ExactFileSnapshot(raw, identity)
GitWorktreeRegistrationToken(
  worktree_identity, gitfile_identity, gitfile_sha256,
  administration_identity, backlink_identity, backlink_sha256,
  registered_path, administration_path
)
OwnerlessGitFacts(accepted_head, observation, registration_token)
observe_lane(root: Path, branch: str) -> tuple[LaneObservation, list[str]]
observe_ownerless_git(root: Path, *, branch: str, accepted_branch: str) -> OwnerlessGitFacts
read_root_bound_regular_file(
  root: Path, relative_path: str, *, maximum_bytes: int
) -> ExactFileSnapshot
git_object_bytes(root: Path, object_spec: str) -> bytes
git_ancestry(root: Path, ancestor: str, descendant: str) -> Literal[
  "ancestor", "diverged", "unverifiable"
]
```

1. Add RED cases for malformed `worktree list --porcelain -z`, duplicate
   registration, target or accepted live-HEAD drift, Git stderr/non-zero, raw
   non-UTF8 output, index/worktree/untracked dirt, `assume-unchanged`,
   `skip-worktree`, same-path/same-ref/same-HEAD delete-recreate, root or component
   symlinks, Chronicle directory swap, accepted-tree symlink/submodule/tree modes,
   duplicate tree records, CRLF bytes, and non-UTF8 blob bytes.
2. Assert every Git subprocess uses literal `git`, byte mode,
   `GIT_OPTIONAL_LOCKS=0`, `shell=False`, and no executable override.
3. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/lanes/retirement/admission/test_git_observation.py \
     tests/unit/lanes/retirement/admission/test_chronicle_observation.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_admission.py \
     tests/unit/coverage/test_lane_resolution_edges.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_effect.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_cas_final_edges.py
   ```

4. Implement the public observation module. Walk file components from pinned
   descriptors with `O_NOFOLLOW`. Derive the serialized lane incarnation from
   the descriptor token, not branch/head/path. Parse exactly one accepted
   `ls-tree -z` record and admit only modes `100644` and `100755`.
5. Run GREEN, module-layout, Ruff, types, and no-compat.
6. Commit:

   ```text
   git commit -S -m 'refactor(resolution): observe ownerless targets exactly'
   ```

**Stop conditions:** any synthetic branch/head/path incarnation remains, Git may
write optional locks, hidden index flags can bypass dirt checks, accepted mode is
not regular, or exact bytes are normalized.

## Task 7: Implement strict native admission and raw-state validation

**OpenSpec alignment:** section 6.

**Files:**

- Create: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/admission.py`
- Modify: `packages/ethos/src/ethos/adapters/store/state/closeout.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/records/current/validation/core.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/records/inventory.py`
- Modify: `packages/ethos-core/src/ethos_core/contracts/branch/roles.py` only if a
  pure strict text parser is required; preserve the existing tolerant reader for
  non-admission call sites.
- Test: `tests/unit/lanes/retirement/test_ownerless_closeout_admission.py`
- Test: `tests/unit/lanes/retirement/test_ownerless_closeout_fence.py`
- Test: `tests/unit/kernel/test_ownerless_state_final_edges.py`
- Test: `tests/unit/coverage/test_ownerless_recovery_final_edges.py`
- Test: `tests/unit/coverage/test_ownerless_cleanup_final_edges.py`

**Public API:**

```text
OwnerlessCloseoutAdmissionError(gap: str, detail: str = "")
OwnerlessCloseoutAdmission, frozen and slots-only, containing facts but no callables
admit_ownerless_closeout(
  *, root: Path, decision_path: Path,
  decision: dict[str, Any], executor_ref: str
) -> OwnerlessCloseoutAdmission
reobserve_ownerless_closeout_under_fence(
  *, admission: OwnerlessCloseoutAdmission,
  fence: dict[str, object]
) -> OwnerlessCloseoutAdmission
observe_ownerless_closeout_state(
  db_path: Path, *, subject: str,
  observed_fence: tuple[str, dict[str, object] | None] | None = None
) -> tuple[str, dict[str, object] | None]
```

1. Add RED cases for canonical decision bytes/digest, Chronicle bytes/mode/
   disposition, strict present-policy TOML/table/field types, custom
   `work_branch_prefix`, executor canonicalization, registration token drift,
   accepted ancestry three-state results, raw lease type corruption, Claim,
   holder, expired/current lease distinctions, damaged SQLite/fence/sidecars,
   invalid current records, exact retry reservation, competing reservation, and
   every post-fence exception path.
2. Require absence-only policy defaults. A present malformed policy file must not
   silently become the default policy.
3. Validate raw lease row and payload types before `HolderRef` parsing and
   `LaneLease.model_validate(..., strict=True)`; reject `bool` where integer is
   expected and reject string coercion for booleans, epochs, path lists, and
   digests.
4. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/lanes/retirement/test_ownerless_closeout_admission.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_fence.py \
     tests/unit/kernel/test_ownerless_state_final_edges.py \
     tests/unit/coverage/test_ownerless_recovery_final_edges.py \
     tests/unit/coverage/test_ownerless_cleanup_final_edges.py
   ```

5. Implement native admission with `OwnerlessCloseoutAdmission` as an immutable
   fact snapshot. The fence-held function must probe the exact fence before and
   from a `finally` boundary after complete re-observation, including unexpected
   exceptions.
6. Keep `closeout/admission.py` at or below 400 effective lines by locating Git
   observation in `observation.py`, current-record validation in its defining
   module, and raw-state validation in `store/state/closeout.py`.
7. Run GREEN, Ruff, types, code-size, module-layout, schemas, and no-compat.
8. Commit:

   ```text
   git commit -S -m 'feat(resolution): admit ownerless closeout natively'
   ```

**Stop conditions:** tolerant present-policy fallback, Pydantic coercion before
raw validation, incomplete Chronicle mode/bytes check, missing after-fence probe,
or mutable/callable admission state.

## Task 8: Reconnect effect, retry, recovery, and cleanup; delete runtime bags

**OpenSpec alignment:** section 7.

**Files:**

- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/effect.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/retry.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/recovery.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/cleanup/core.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/_effects.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/lane.py`
- Modify: `packages/ethos/src/ethos/adapters/mutation/resolution/receipts.py`
- Modify: `packages/ethos/src/ethos/adapters/store/state/closeout.py`
- Delete the retired external-verifier adapter package under ownerless closeout.
- Delete the retired provider-response edge test.
- Modify all ownerless effect/retry/recovery/cleanup tests under
  `tests/unit/lanes/retirement/` and final-edge tests under `tests/unit/coverage/`

**Required order:**

```text
completed-effect recovery precheck
exact pre-fence native admission and reservation classification
release/reset the old exact zero-effect fence and reservation, when classified
acquire a fresh exact fence
complete under-fence re-observation
persist typed reservation
no-force worktree removal
accepted-ref verification
exact target-ref delete CAS
postconditions
immutable receipt
fence CAS release
reservation removal
```

1. Add or update RED cases for same-head and descendant accepted-head retry,
   divergence, target drift, decision/Chronicle drift, descendant classification
   before competition, removal failure re-observation, crash after each durable
   boundary, completed-effect recovery before target observation, receipt-present
   effect-free cleanup, dangling paths, post-CAS exception, three-state ref/
   registration/fence probes, and cleanup ordering.
2. Run RED:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/lanes/retirement/test_ownerless_closeout_effect.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_effect_final_edges.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_cas_final_edges.py \
     tests/unit/lanes/retirement/test_ownerless_no_effect_retry.py \
     tests/unit/lanes/retirement/test_ownerless_closeout_recovery.py \
     tests/unit/lanes/retirement/test_ownerless_cleanup_recovery.py \
     tests/unit/coverage/test_ownerless_recovery_final_edges.py \
     tests/unit/coverage/test_ownerless_cleanup_final_edges.py
   ```

3. Connect admission directly. Remove `OwnerlessCloseoutRuntime`,
   `ResolutionRuntime`, `_ownerless_runtime()`, `_resolution_runtime()`, provider
   process execution, callback fields, and callable dictionaries.
4. Replace the overloaded `fence_acquired` error flag with explicit
   `OwnerlessCloseoutPhase` and reservation recovery state. Release a pre-effect
   fence only when exact ownership and zero durable effect are proved; retain
   reservation visibility at or after effect.
5. Make completed-effect recovery validate decision and Chronicle before ordinary
   worktree observation. For a possible zero-effect retry, first complete exact
   pre-fence admission and reservation classification; only then release/reset the
   old exact fence and reservation, acquire a fresh fence, and complete the full
   under-fence re-observation before a new reservation or effect.
6. Run GREEN, then the entire lane-resolution, state, crash, retry, and
   three-state suite.
7. Run direct-import and residue checks:

   ```text
   rg -n 'OwnerlessCloseoutRuntime|ResolutionRuntime|_ownerless_runtime|_resolution_runtime' \
     packages tests
   tools/ci/scripts/run-no-compat.sh
   tools/ci/scripts/run-import-linter.sh
   ```

   Expected: `rg` has no production or test result.
8. Commit:

   ```text
   git commit -S -m 'refactor(resolution): make ownerless effect native'
   ```

## Task 9: Add declaration-driven mandatory executable coupling audit

**OpenSpec alignment:** section 8.

**Files:**

- Modify first: `openspec/changes/native-lane-resolution-authority/scope.toml` to
  include the exact contract, audit, schema, and test paths below
- Modify: `system/coupling.toml`
- Modify: `packages/ethos-core/src/ethos_core/contracts/registry/declarations.py`
- Create declaration-only:
  `packages/ethos/src/ethos/repository/policy/coupling/execution/__init__.py`
- Create: `packages/ethos/src/ethos/repository/policy/coupling/execution/audit.py`
- Modify: `packages/ethos/src/ethos/repository/policy/coupling/core.py`
- Modify: `system/schemas/kernel/coupling-audit.schema.json`
- Create: `tests/unit/governance/test_coupling_executables.py`
- Modify: `tests/unit/governance/validation/test_schemas.py`
- Modify: `tests/architecture/test_product_boundaries.py`

**Contract fields and interface:**

```text
CouplingBinding.mandatory_paths: tuple[str, ...]
CouplingBinding.declared_executables: tuple[str, ...]
CouplingBinding.audit_root_bound: bool
mandatory_executable_gaps(
  root: Path, declaration: CouplingDeclaration
) -> list[str]
```

1. Add RED fixtures for an undeclared literal executable, dynamic `argv[0]`, a
   command string, `shell=True`, non-`None` `executable=`, a declared literal
   `git`, a path escaping the audit root, and optional semantic-attestation/
   control-replacement modules outside mandatory paths.
2. Declare the lane-resolution mandatory paths and only `git` as the external
   executable. Do not declare `tar`, a Python interpreter, a shell, or a provider
   executable for the lifecycle effect.
3. Implement AST inspection only for declaration-listed, audit-root-bound paths.
   Do not scan all repository subprocess use and do not add a provider-name
   blacklist.
4. Run:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/governance/test_coupling_executables.py \
     tests/unit/governance/validation/test_schemas.py \
     tests/architecture/test_product_boundaries.py
   tools/ci/scripts/run-ethos-lane.sh quality coupling-audit --json
   tools/ci/scripts/run-ethos-lane.sh quality schemas --json
   tools/ci/scripts/run-config-lint.sh
   ```

5. Commit:

   ```text
   git commit -S -m 'feat(governance): audit mandatory lifecycle executables'
   ```

**Stop conditions:** whole-repository overreach, optional-adapter false positives,
dynamic executable acceptance, shell acceptance, or provider-specific blacklist.

## Task 10: Converge current tracked truth to zero retired-provider residue

**OpenSpec alignment:** section 9.

**Files:** every current tracked path returned by the exact scans below, including
source, tests, schemas, canonical specs, command reference, active plans,
Claims, Chronicle, and archived OpenSpec carriers. Git history and local records
are excluded.

1. Build the complete provider-identity inventory in an ignored task-local file.
   Include the acronym, expanded names, wire/schema identity, executable command,
   adapter path, response fields, and retired test/path identities. Never persist
   the inventory values in tracked source. Fail closed when the inventory path is
   missing, empty, contains a sentinel, or contains a blank entry:

   ```text
   set -euo pipefail
   : "${RETIRED_PROVIDER_IDENTITIES_FILE:?set ignored inventory path}"
   test -s "$RETIRED_PROVIDER_IDENTITIES_FILE"

   allow_match_or_no_match() {
     if "$@"; then
       rc=0
     else
       rc=$?
     fi
     case "$rc" in
       0|1) return 0 ;;
       *) return "$rc" ;;
     esac
   }

   if rg -n '(^[[:space:]]*$|task-local|placeholder|sentinel)' \
     "$RETIRED_PROVIDER_IDENTITIES_FILE"; then
     inventory_guard_rc=0
   else
     inventory_guard_rc=$?
   fi
   test "$inventory_guard_rc" -eq 1
   tracked_paths="$(mktemp)"
   trap 'rm -f "$tracked_paths"' EXIT
   git ls-files > "$tracked_paths"
   while IFS= read -r identity; do
     test -n "$identity"
     allow_match_or_no_match git grep -l -I -i -F -- "$identity" .
     allow_match_or_no_match rg -i -F -- "$identity" "$tracked_paths"
   done < "$RETIRED_PROVIDER_IDENTITIES_FILE"
   ```

2. Delete the retired adapter package and provider-response test. Replace every
   remaining current tracked occurrence with neutral repository-role wording
   while preserving dates, decisions, actions, evidence digests, limitations,
   and chronology.
3. Remove the literal token from this design, this implementation plan, and the
   active OpenSpec Change before the final scan. Keep the prevention mechanism
   generic through closed contracts and executable coupling declarations.
4. Recompute only digests made stale by tracked text edits, then validate Claims:

   ```text
   tools/ci/scripts/run-ethos-lane.sh quality claims --json
   openspec validate native-lane-resolution-authority --strict --json
   ```

5. Prove zero current tracked residue for every frozen identity and require both
   tracked-content and tracked-filename scans to remain empty:

   ```text
   set -euo pipefail
   : "${RETIRED_PROVIDER_IDENTITIES_FILE:?set ignored inventory path}"
   test -s "$RETIRED_PROVIDER_IDENTITIES_FILE"

   require_no_match() {
     output="$1"
     shift
     if "$@" > "$output" 2>&1; then
       rc=0
     else
       rc=$?
     fi
     case "$rc" in
       1) return 0 ;;
       0) cat "$output" >&2; return 1 ;;
       *) cat "$output" >&2; return "$rc" ;;
     esac
   }

   scan_dir="$(mktemp -d)"
   trap 'rm -rf "$scan_dir"' EXIT
   require_no_match "$scan_dir/inventory-guard" \
     rg -n '(^[[:space:]]*$|task-local|placeholder|sentinel)' \
     "$RETIRED_PROVIDER_IDENTITIES_FILE"
   git ls-files > "$scan_dir/tracked-paths"
   ordinal=0
   while IFS= read -r identity; do
     test -n "$identity"
     ordinal=$((ordinal + 1))
     require_no_match "$scan_dir/content-$ordinal" \
       git grep -n -I -i -F -- "$identity" .
     require_no_match "$scan_dir/filename-$ordinal" \
       rg -n -i -F -- "$identity" "$scan_dir/tracked-paths"
   done < "$RETIRED_PROVIDER_IDENTITIES_FILE"
   ```

6. Commit:

   ```text
   git commit -S -m 'docs(governance): remove retired provider authority residue'
   ```

**Stop conditions:** a tracked match remains, a special-case blacklist is added,
a historical Git commit is rewritten, or local predecessor records are edited.

## Task 11: Pay branch-owned quality debt and perform independent review

**OpenSpec alignment:** section 10.

**Files:**

- Refine: `packages/ethos/src/ethos/adapters/mutation/resolution/closeout/admission.py`
- Split: `tests/unit/coverage/test_lane_resolution_record_edges.py`
- Create declaration-only: `tests/unit/coverage/lane_resolution_records/__init__.py`
- Create: `tests/unit/coverage/lane_resolution_records/test_current_records.py`
- Create: `tests/unit/coverage/lane_resolution_records/test_clear_and_reservations.py`
- Modify OpenSpec scope before writing the new test paths
- Do not modify `.config/checks/ruff/ratchet.toml` except to remove already-paid
  entries when the owner gate generates an evidence-backed shrink

1. Run branch-focused Ruff and code-size to capture exact debt:

   ```text
   tools/ci/scripts/run-python-lint.sh
   tools/ci/scripts/run-ethos-lane.sh quality code-size --json
   ```

2. Remove branch-owned `EM101`, `TRY003`, and `PLR0911` findings by using stable
   module constants/helpers and by splitting decision branches. Keep admission at
   or below 400 effective lines.
3. Move record tests into the two semantic files above so no test file exceeds
   the configured hard ceiling. Do not raise the ceiling and do not create more
   than two direct modules in the new directory.
4. Run:

   ```text
   uv run --package ethos python -m pytest -q \
     tests/unit/coverage/lane_resolution_records/test_current_records.py \
     tests/unit/coverage/lane_resolution_records/test_clear_and_reservations.py
   tools/ci/scripts/run-python-lint.sh
   tools/ci/scripts/run-ethos-lane.sh quality code-size --json
   tools/ci/scripts/run-module-layout.sh
   ```

5. Commit quality repayment separately:

   ```text
   git commit -S -m 'refactor(resolution): pay native closeout quality debt'
   ```

6. Request an independent task review of contracts/records, preservation,
   observation/admission, effect/recovery, coupling, and truth convergence. Fix
   every Important or Critical finding in a focused signed commit and rerun that
   slice's complete test set.

**Stop conditions:** any baseline grows, any Important/Critical finding remains,
or the test split changes semantics instead of file ownership.

## Task 12: Complete proof, generic parity, and official archive

**OpenSpec alignment:** section 11.

1. Confirm a clean, current candidate base:

   ```text
   tools/ci/scripts/run-ethos-lane.sh status --json
   git merge-base --is-ancestor candidate/dev HEAD
   git status --short
   ```

2. Run focused and full gates on one stable HEAD:

   ```text
   tools/ci/scripts/run-python-lint.sh
   tools/ci/scripts/run-python-tests.sh
   tools/ci/scripts/run-config-lint.sh
   tools/ci/scripts/run-shell-lint.sh
   tools/ci/scripts/run-markdown-lint.sh
   tools/ci/scripts/run-format-selection.sh
   tools/ci/scripts/run-module-layout.sh
   tools/ci/scripts/run-no-compat.sh
   tools/ci/scripts/run-import-linter.sh
   tools/ci/scripts/run-ethos-lane.sh quality types --json
   tools/ci/scripts/run-ethos-lane.sh quality schemas --json
   tools/ci/scripts/run-ethos-lane.sh quality code-size --json
   tools/ci/scripts/run-ethos-lane.sh quality coupling-audit --json
   tools/ci/scripts/run-ethos-lane.sh quality claims --json
   tools/ci/scripts/run-ethos-lane.sh quality docs --json
   tools/ci/scripts/run-ethos-lane.sh openspec \
     --change native-lane-resolution-authority --lifecycle --json
   openspec validate native-lane-resolution-authority --strict --json
   git diff --check
   ```

3. Execute generic parity in the admitted lane and commit its evidence:

   ```text
   tools/ci/scripts/run-ethos-lane.sh parity gaps --json
   tools/ci/scripts/run-ethos-lane.sh parity shadow \
     --adopter generic --target . --execute --write-evidence --json
   git commit -S -m 'test(parity): refresh native lane resolution evidence'
   ```

4. Check only implementation tasks `2.x` through `10.x` and proof inputs
   `11.1` through `11.2` that are backed by fresh evidence. Update the
   Chronicle and active native Claim without claiming archive, land, accepted
   closeout, or publication, then commit those evidence inputs.
5. Execute the final exact-HEAD pre-archive proof and confirm the isolated
   archive preflight on that proven HEAD:

   ```text
   tools/ci/scripts/run-ethos-lane.sh prove \
     --execute --expect-head "$(git rev-parse HEAD)" --json
   tools/ci/scripts/run-ethos-lane.sh openspec \
     --change native-lane-resolution-authority --lifecycle --json
   ```

6. In one evidence-only commit, record the proof HEAD/receipt and check the
   rewritten `11.3`. Do not claim or attempt a second self-referential
   pre-archive proof for that checklist-only commit. Immediately archive; if the
   calendar date changed from 2026-07-25, first update scope to the actual dated
   archive create path and rerun prewrite.
7. Officially archive, read the actual archive path from JSON, migrate the native
   Claim carrier to that dated path, keep the native Claim active, and mark the
   predecessor Claim superseded in the same signed commit:

   ```text
   openspec archive native-lane-resolution-authority --yes --json
   openspec validate --all --strict --json
   tools/ci/scripts/run-ethos-lane.sh openspec --lifecycle --json
   git commit -S -m 'docs(openspec): archive native lane resolution authority'
   ```

8. Because archive and carrier migration changed HEAD, rerun Claim validation,
   the zero-residue scan, report, and exact-HEAD proof:

   ```text
   tools/ci/scripts/run-ethos-lane.sh quality claims --json
   tools/ci/scripts/run-ethos-lane.sh report --json
   tools/ci/scripts/run-ethos-lane.sh prove \
     --execute --expect-head "$(git rev-parse HEAD)" --json
   ```

**Stop conditions:** HEAD moves inside a gate bundle, parity remains pending,
the checklist claims archive/post-archive work, archive validation fails, proof
is dry-run only, or archive proof is bound to a pre-archive HEAD.

## Task 13: Final refresh, land, accepted closeout, publish readiness, housekeeping

**OpenSpec alignment:** section 12.

1. Refresh again immediately before land:

   ```text
   tools/ci/scripts/run-ethos-lane.sh lane refresh-base \
     --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
   ```

   If HEAD changes, rerun every Task 12 gate, parity check, and executed proof.
   If refresh conflicts, stop; do not hand-resolve a proven HEAD.

2. Land the exact proven HEAD to candidate:

   ```text
   tools/ci/scripts/run-ethos-lane.sh land \
     --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
   ```

3. From `<accepted-root>`, run accepted-root closeout dry-run as a distinct
   audited transition after candidate/accepted facts are current. When control
   paths changed, ETHOS MUST defer with
   `incumbent_or_bootstrap_verifier_required`; obtain a candidate-external
   one-shot control-replacement verifier receipt and supply its absolute path.
   The product repository does not mint that external receipt:

   ```text
   cd <accepted-root>
   tools/ci/scripts/run-ethos-lane.sh status --json
   tools/ci/scripts/run-ethos-lane.sh land \
     --closeout --control-verifier-receipt <absolute-path> --json
   tools/ci/scripts/run-ethos-lane.sh land \
     --closeout --control-verifier-receipt <absolute-path> \
     --apply --authorize --expect-head "$(git rev-parse HEAD)" --json
   ```

4. Report local publication readiness only:

   ```text
   tools/ci/scripts/run-ethos-lane.sh publish --json
   ```

   Do not run `git push`.

5. Re-observe live ownership and absorption before each retirement. Retire the
   landed successor through holder-bound landed retirement. The three clean,
   missing-lease predecessor mistake lanes below are currently diverged and do
   not have exact absorption; they require one-at-a-time Chronicle-bound
   `preserve-retire` decisions after accepted truth contains the exact targets,
   heads, reasons, and recovery boundary:

   For every later `preserve-retire` target, create one separate Chronicle only
   after accepted truth contains it. The Chronicle must be read from the accepted
   control checkout and begin with UTF-8 front matter containing
   `event: lane_resolution/preserve-retire`, the exact observed `target_head`,
   and exactly one selector: literal `target_branch` or
   `target_branch_sha256`, computed from the branch UTF-8 bytes with no newline.
   Its working bytes, accepted-tree blob, and decision digest must match. Recheck
   the binding before receipt reservation/package creation and again after package
   verification before source removal. A later target, Chronicle, lease, Claim,
   dirt, inventory, or HEAD drift stops that target only. If the final Chronicle
   or observation check blocks retirement after package verification, retain the
   source and package under a `preserved_retirement_blocked` receipt containing
   the exact permitted blocker; do not record retirement.

   ```text
   work/20260724-native-lane-resolution-authority-successor
   work/20260724-native-lane-resolution-authority
   task-owned retired-provider predecessor at head
     c3075ebc6cd581212e2c2ff138fbd2c4e7df9cc8, identified by branch-ref
     SHA-256 dda7e65c0339a066f31c46ddecdb103b254a71061d730d8c71b9b08d2f613911
   work/20260723-legacy-lane-resolution-record-freeze-capability
   ```

   Retire the successor only after a fresh preview proves it is landed:

   ```text
   branch=work/20260724-native-lane-resolution-authority-successor
   head="$(git rev-parse --verify "$branch")"
   tools/ci/scripts/run-ethos-lane.sh lane retire landed \
     --branch "$branch" --expect-head "$head" --apply --json

   predecessor_branch="$(
     git for-each-ref --format='%(refname:short)' refs/heads/work/ |
     while IFS= read -r branch; do
       digest="$(printf '%s' "$branch" | shasum -a 256 | awk '{print $1}')"
       if [ "$digest" = "dda7e65c0339a066f31c46ddecdb103b254a71061d730d8c71b9b08d2f613911" ]; then
         printf '%s\n' "$branch"
       fi
     done
   )"
   test -n "$predecessor_branch"
   test "$(printf '%s\n' "$predecessor_branch" | wc -l | tr -d ' ')" = 1
   head="$(git rev-parse --verify "$predecessor_branch")"
   test "$head" = c3075ebc6cd581212e2c2ff138fbd2c4e7df9cc8
   ```

   Run `lane status --json` and resolution inventory before every predecessor.
   For each exact branch/HEAD, create and apply a Chronicle-bound
   `preserve-retire` decision through `ethos lane resolution` with required
   break-glass and irreversible confirmation. Stop on any active lease/Claim,
   dirt, stale observation, invalid/pending/partial state, or changed HEAD. Do
   not route these diverged predecessors through `lane retire landed`, and do
   not invent a supersession or absorption relationship.

6. Remove only task-created review packets, scratch files, `__pycache__`, pytest
   caches, and temporary proof output. Leave foreign lanes, `.venv`, historical
   records, SQLite, session JSONL, and IDE databases untouched.
7. Finish with:

   ```text
   git -C <accepted-root> status --short --branch
   git -C <candidate-root> status --short --branch
   tools/ci/scripts/run-ethos-lane.sh lane status --json
   tools/ci/scripts/run-ethos-lane.sh report --json
   ```

**Completion conditions:** current tracked retired-provider residue is zero;
mandatory lifecycle executables are declaration-bound; native admission/effect/
retry/recovery are complete; runtime bags are gone; every required gate and
archive-HEAD proof passes; candidate and accepted closeout are distinct and
complete; local publish readiness is reported without push; task-owned lanes and
scratch are closed; protected roots and surviving foreign lanes are clean and
untouched.
