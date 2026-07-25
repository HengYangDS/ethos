## Context

ETHOS already owns the irreversible ownerless-retirement effect: decision and
Chronicle records, SQLite exclusion, durable reservation, no-force worktree
removal, exact Git ref CAS, postconditions, immutable receipts, and crash
recovery. An unrelated out-of-process verifier and mixed predecessor record roots
were later placed inside that authority path. The result is split authority,
provider vocabulary in kernel contracts, historical records influencing current
effects, and callback/runtime bags that hide the concrete owner of behavior.

The original implementation lane also fell materially behind `candidate/dev`.
Native refresh reported real conflicts, so implementation moved to a successor
lane created from current candidate truth. The old lane remains a clean rollback
carrier. Product code is replayed by semantic slice; it is not bulk cherry-picked.

Current candidate truth includes staged-index recovery package v2 from commit
`8fcea306d`: `tracked.patch`, `index.patch`, and `index_patch_sha256`. The old
preservation commit `21142430c` predates that complete current shape and cannot be
replayed as a whole.

## Goals / Non-Goals

**Goals:**

- Make Work Lane observation, admission, records, effect, retry, recovery, and
  cleanup self-contained inside ETHOS repository and local-state authority.
- Enforce refresh-first implementation and successor-lane semantic replay after a
  real native-refresh conflict.
- Preserve the old lane as rollback carrier until landed absorption is exact.
- Preserve one exact CAS, one exact binding, one exact typed reservation, and one
  immutable receipt path.
- Separate current records from immutable history without a data migration.
- Make invalid or pending current records visible and fail closed.
- Observe Git, Chronicle, policy, worktree registration, lease, Claim, and fence
  facts byte- and descriptor-exactly.
- Replace synthetic branch/head/path incarnation with a descriptor-bound Git
  worktree registration token.
- Preserve staged-index recovery package v2 while making archive creation native,
  byte exact, descriptor bound, and bounded in memory.
- Remove runtime/callback bags and import concrete owners directly.
- Prevent undeclared mandatory lifecycle executables through generic,
  declaration-driven coupling audit.
- Remove retired-provider authority residue from the current tracked tree without
  rewriting Git history or local predecessor records.
- Pay branch-owned Ruff, module-layout, and code-size debt without baseline
  expansion.

**Non-Goals:**

- No compatibility alias, dual reader, dual writer, provider adapter, facade,
  single-implementation Protocol, package-root export, or runtime service bag.
- No archive/freeze/tombstone migration, activation marker, migration journal,
  or destructive history cleanup.
- No process-table occupancy substitute.
- No workspace-key migration or Work Lane creation-policy change.
- No whole-commit replay of predecessor preservation code.
- No rewrite of Git history, historical local records, SQLite history,
  virtual environments, or IDE/session metadata.
- No retirement of a foreign Work Lane during implementation acceptance.
- No remote publication or hosted mutation.

## Decisions

### 1. Refresh-first successor semantic replay

Before any implementation slice, the successor must show `candidate/dev` as an
ancestor. If candidate advances, native `ethos lane refresh-base` runs first. A
real refresh conflict aborts and restores the lane; work continues only in a new
successor started from current candidate.

The predecessor lane is read-only rollback material. Its commits may be inspected
with `git show`, but product commits are not cherry-picked. Each slice starts with
current-candidate RED tests, replays only still-valid semantics, receives focused
review, and lands as a signed commit.

Alternative rejected: continue on the stale lane and refresh at the end. That
would multiply conflicts and bind proof to obsolete candidate truth.

### 2. One non-destructive current-record authority cut

Current authority moves to:

```text
<accepted>-records/recovery/lane-resolution-v2/
```

Predecessor history remains at:

```text
<accepted>-records/recovery/lane-resolution/
<registered-worktree>/build/artifacts/lane-resolution/
```

`current_record_root()` is the only root used by decide, apply, retry, recovery,
receipt, clear, and current inventory. `historical_record_roots()` is an
independent read-only locator. There is no current-to-history fallback and
current clear never deletes history.

### 3. Provider-neutral typed records

`LaneResolutionReceipt` writes schema version 3. Its ownerless binding contains
exactly:

```text
executor_ref
decision_sha256
accepted_branch
accepted_head
target_digest
target_binding_digest
postcondition_digest
```

`OwnerlessCloseoutReservation` is the single schema-version-2 owner of
reservation shape and phase/recovery invariants. Clear receipts carry version 1.
Decision version 1 remains unchanged. Closed models and schemas reject provider-
prefixed fields, unexpected fields, invalid OIDs, and non-canonical bytes.

Current inventory enumerates decisions, manifests, receipts, clears, and
reservations. It reports `decision_pending` and blocking invalid-current-record
facts instead of treating parse failure as absence.

### 4. Fixed, byte-exact Git observation

Mandatory lifecycle Git execution uses literal `git`, byte stdout/stderr,
`GIT_OPTIONAL_LOCKS=0`, `shell=False`, and no executable override. Git failures or
malformed output are unverifiable.

Cleanliness includes porcelain-v2 status, worktree diff, staged diff, exact
untracked inventory, and rejection of `assume-unchanged` and `skip-worktree`
entries. Exact blobs, patches, and paths are not normalized through text.

### 5. Descriptor-bound Git worktree registration token

`GitWorktreeRegistrationToken` binds the target worktree directory, target `.git`
gitfile, linked-worktree administration directory, administration `gitdir`
backlink, their descriptor identities, their exact pointer bytes, and their exact
paths. Components are opened relative to pinned parent descriptors with
`O_NOFOLLOW`, and visible/descriptor identities are compared before and after the
read.

The token replaces `hash(branch, head, path)` as the decision incarnation. A
same-path, same-ref, same-HEAD delete/recreate changes the token and blocks the old
decision.

### 6. Exact Chronicle, policy, and local-state admission

Chronicle working bytes are read from a pinned repository-root descriptor.
Accepted bytes come from exact Git object plumbing only after exactly one
`ls-tree -z` record proves regular blob mode `100644` or `100755`. Symlink,
submodule, tree, duplicate, absent, malformed, or failed observations block.
Working bytes, accepted bytes, declared digest, and required disposition must all
match.

An absent `.ethos/workspace.toml` uses default branch roles. A present file must
be valid TOML with a strict `branch_roles` table and exact raw field types. A
malformed present file cannot silently select defaults. The configured
`work_branch_prefix` remains authoritative.

Lease and fence readers validate raw SQLite row and JSON types before model
construction. Damaged schema, payload, sidecar, holder, lease, Claim, or fence
facts are unverifiable, not absent.

### 7. Immutable fact-only admission

Public API remains:

```text
OwnerlessCloseoutAdmission, frozen and slots-only
admit_ownerless_closeout(
  *, root: Path, decision_path: Path,
  decision: dict[str, Any], executor_ref: str
) -> OwnerlessCloseoutAdmission
reobserve_ownerless_closeout_under_fence(
  *, admission: OwnerlessCloseoutAdmission,
  fence: dict[str, object]
) -> OwnerlessCloseoutAdmission
```

The admission snapshot contains only immutable observed facts. It contains no
functions, command runners, state stores, Protocols, or service objects.

Pre-fence admission validates exact decision bytes, Chronicle, strict policy,
executor, accepted and target Git facts, registration token, clean ownerless
state, accepted ancestry, current-record integrity, reservation classification,
and binding digests.

Fence-held admission repeats the complete observation. The after-fence probe runs
from a `finally` boundary for every exception class. A missing, changed, damaged,
or competing fence blocks effect and cannot authorize cleanup.

### 8. Exact effect, retry, recovery, and cleanup order

The order is:

```text
completed-effect recovery precheck
-> exact pre-fence native admission and reservation classification
-> release/reset the old exact zero-effect fence and reservation, when classified
-> acquire a fresh exact fence
-> complete under-fence re-observation
-> typed reservation persistence
-> no-force worktree removal
-> accepted-ref verification
-> exact target-ref deletion CAS
-> explicit postconditions
-> immutable receipt
-> fence release CAS
-> reservation removal
```

Completed-effect recovery validates decision and Chronicle before ordinary target
observation because a completed effect removed the target worktree.

A zero-effect retry may rebind only after exact pre-fence admission classifies
decision, executor, target, registration token, coordination facts, and the
reservation as the same zero-effect retry, no effect occurred, and current
accepted HEAD equals or descends from the reserved accepted HEAD. Descendant
classification precedes ordinary competing-reservation rejection. ETHOS then
releases the old exact fence and reservation, acquires a fresh fence, and
completes full under-fence re-observation before a new reservation or effect.

Cleanup uses explicit phase and recovery state, not `fence_acquired: bool`.
Pre-effect exceptions may release only a provably owned zero-effect fence. Effect
or later exceptions preserve visible reservation state and classify the
transition as partial or unknown. Receipt-present cleanup is effect-free and
releases the fence before deleting the reservation.

`OwnerlessCloseoutRuntime`, `ResolutionRuntime`, `_ownerless_runtime()`,
`_resolution_runtime()`, and all callable/runtime dictionaries are deleted.
Tests patch concrete consumer module boundaries.

### 9. Preserve current recovery package v2

Preservation uses fixed Git and stdlib `tarfile`. Untracked members are walked
from pinned descriptors with no-follow semantics and bounded-memory spooling.
External `tar` is removed from mandatory lifecycle execution.

New packages retain:

```text
repository.bundle
tracked.patch
index.patch
untracked.tar, when present
manifest.json with package_format_version=v2,
  patch_sha256, index_patch_sha256, and archive digest
```

Alternative rejected: cherry-pick predecessor preservation commit `21142430c`.
It would regress staged-index current truth from candidate commit `8fcea306d`.

### 10. Generic executable coupling governance

`system/coupling.toml` declares audit-root-bound mandatory lifecycle paths and
allowed external executables. Lane resolution declares only literal `git`.
SQLite, JSON, schemas, descriptors, and `tarfile` are in-process protocols.

A declaration-driven AST audit scans only mandatory paths and rejects undeclared
executables, dynamic `argv[0]`, command strings, `shell=True`, executable
overrides, and path escapes. Optional semantic-attestation, control-replacement,
release-profile, and policy adapters outside the mandatory path remain unaffected.
No provider-name blacklist is added.

### 11. Module and quality governance

The `_observation.py` to `observation.py` move is a net-neutral rename. The layout
gate changes only so existing-directory growth requires
`current_count > previous_count`; five-to-six growth and burst rules remain
blocking.

Every `__init__.py` stays docstring-only and all imports name defining modules.
`closeout/admission.py` remains within the logic soft limit. The enlarged record
edge test is split into a two-module semantic subpackage. Branch-owned `EM101`,
`TRY003`, and `PLR0911` findings are fixed without expanding Ruff or code-size
baselines.

### 12. Current truth, proof, archive, land, and housekeeping

The current tracked tree is normalized to zero retired-provider
identifier/path/field/test residue,
including current Claims, Chronicle, active plans, canonical specs, and archived
OpenSpec carriers. Dates, actions, decisions, evidence digests, limitations, and
chronology remain. Git history and local predecessor records are untouched.

Focused tests precede each slice. Full gates, generic parity, and exact-HEAD
executed proof run on a stable signed HEAD. Official OpenSpec archive changes
HEAD, so validation and executed proof run again after archive.

Final candidate refresh precedes land. If it changes HEAD, all proof is rerun.
Land to candidate, accepted-root closeout, and local publish readiness are
separate transitions. No push occurs.

Only task-owned, exactly absorbed successor/predecessor lanes and task-created
scratch/caches are retired or deleted. Foreign lanes, virtual environments,
local records, SQLite history, and session metadata remain untouched.

## Risks / Trade-offs

- **Descriptor identities are platform facts** -> Keep them inside native
  observation/admission and serialize only a deterministic token into the existing
  incarnation field.
- **Exact no-lock Git observation may expose previously hidden failures** -> Fail
  closed; authority must not depend on an observation that could not be proved.
- **Strict present-policy parsing differs from tolerant reader behavior** -> Add a
  strict admission-only path and preserve tolerant behavior for unrelated reader
  projections.
- **Semantic replay takes longer than cherry-pick** -> It prevents regression of
  current candidate truth and makes each slice independently reviewable.
- **Tracked vocabulary normalization touches history carriers** -> Preserve
  historical meaning and digests, but remove the current product dependency token;
  do not rewrite Git history or local records.
- **Generic executable audit may overreach** -> Bind it to declaration-listed
  mandatory paths only and test optional adapters explicitly.

## Migration Plan

1. Confirm current successor ancestry and strict carrier validity; refresh first
   whenever candidate advances.
2. Replay strict contracts, record roots, inventory, clear, and typed reservation
   slices with RED/GREEN tests and signed reviews.
3. Port descriptor-safe preservation onto candidate recovery package v2, retaining
   staged-index recovery.
4. Correct the net-neutral module-rename gate without changing growth limits.
5. Implement fixed-byte Git/Chronicle observation and descriptor-bound
   registration tokens.
6. Implement strict native admission and raw-state validation.
7. Reconnect effect/retry/recovery/cleanup in the fixed order and delete provider
   execution plus runtime/callback bags.
8. Add declaration-driven mandatory executable coupling audit.
9. Normalize current tracked provider residue, pay branch-owned quality debt, and
   complete independent review.
10. Run full gates, generic parity, exact-HEAD proof, official archive, and
    archive-HEAD proof.
11. Refresh once more, land, perform audited accepted-root closeout, report local
    publish readiness, and retire only exactly absorbed task-owned lanes.

Rollback before land is removal of the successor after evidence review; the old
lane remains the rollback carrier. After land, rollback is a new governed Change.
Historical records never regain automatic current authority.

## Stop Conditions

Stop mutation when candidate is not an ancestor, refresh conflicts, current
candidate recovery package v2 would regress, any authority fact is unverifiable,
the registration token or fence changes, a required quality/coupling/residue/
parity/Claim/OpenSpec/proof gate remains gapped, candidate advances after proof,
archive HEAD lacks fresh proof, or lane ownership/absorption is not exact.

## Open Questions

None. Authority, replay, observation, contract, state-machine, coupling, proof,
and closeout boundaries are decided.
