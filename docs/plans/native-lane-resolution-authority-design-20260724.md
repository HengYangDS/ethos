---
subject: ethos:native-lane-resolution-authority-design-20260724
role: plan
state: active
relations:
  derives_from: native-lane-resolution-authority
---

# Native Lane Resolution Authority Design

Status: approved for implementation after successor-lane baseline convergence.

Purpose: define the self-contained ETHOS authority, observation, record, effect,
recovery, coupling, proof, and closeout boundaries for Work Lane resolution while
removing an unrelated provider from current product truth.

See also: [Implementation Plan](native-lane-resolution-authority-implementation-plan-20260724.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Command Plane](../reference/command-plane.md).

## Decision

ETHOS owns the complete Work Lane lifecycle. Clean ownerless retirement uses one
native chain:

```text
exact decision and Chronicle snapshot
-> completed-effect recovery precheck
-> exact pre-fence configured-policy, Git, worktree-registration, record,
   state, and reservation admission/classification
-> release/reset the old exact zero-effect fence and reservation, when classified
-> acquire a fresh SQLite target fence
-> complete under-fence re-observation
-> typed durable reservation
-> no-force worktree removal
-> accepted-ref verification and exact target-ref CAS
-> explicit postconditions
-> immutable completion receipt
-> fence CAS release
-> reservation removal
```

No out-of-process admission provider is an ETHOS subsystem, dependency, adapter,
authority source, runtime requirement, or compatibility boundary. The final
current tracked tree contains no retired-provider identity, executable call,
adapter path, response field, fixture, or active guidance. Historical carriers
retain only provider-neutral semantics; Git history and ignored or external
local records are not rewritten.

## Baseline convergence and successor authority

Implementation is refresh-first. A Work Lane that is not based on the current
configured candidate branch cannot receive more product changes.

The original lane diverged materially from the current candidate and native
`ethos lane refresh-base` encountered real conflicts. Therefore implementation
continues in the successor Work Lane created from the current candidate. The
original lane remains clean and registered as a rollback carrier until the
successor has landed and exact absorption has been proved.

The successor does not bulk cherry-pick implementation commits. It replays each
approved semantic slice against current candidate truth, with a fresh failing
test, focused review, and signed commit. A conflict or candidate-truth regression
stops the slice rather than selecting an old side mechanically.

This rule is especially strict for preservation. Candidate commit `8fcea306d`
already made recovery package format v2 preserve both `tracked.patch` and
`index.patch`. Old preservation commit `21142430c` predates that complete shape
and must not be cherry-picked as a unit. Its descriptor-bound archive work may be
reapplied only while retaining package format v2, `index.patch`,
`index_patch_sha256`, and the existing staged-index recovery tests.

## Authority boundaries

| Concern | Native owner |
| --- | --- |
| Branch role and accepted policy | Exact repository configuration, with absence-only defaults |
| Accepted and target refs | Fixed-literal Git observation |
| Worktree registration lifetime | Descriptor-bound Git worktree registration token |
| Decision and current-record integrity | Versioned ETHOS current record root |
| Lease, Claim, holder, fence, and effect exclusion | Strict raw SQLite/local-state observation |
| Chronicle authority | Root-bound working bytes plus exact accepted-tree blob bytes and mode |
| Irreversible effect | ETHOS no-force worktree removal and exact Git ref CAS |
| Completion claim | Postcondition-bound immutable receipt and Chronicle |
| Historical records | Opaque read-only history, never current effect authority |

No provider response, process-table occupancy guess, compatibility shim,
callback table, Protocol wrapper, or host control plane participates in the
chain.

## Current and historical record topology

```text
current:  <accepted>-records/recovery/lane-resolution-v2/
history:  <accepted>-records/recovery/lane-resolution/
          <worktree>/build/artifacts/lane-resolution/
```

Current decide, apply, retry, recovery, receipt, clear, and inventory paths use
only `current_record_root()`. `historical_record_roots()` is an independent,
read-only locator for explicit history inspection. Current code does not fall
back to history, parse predecessor effect bindings as current, or delete history.

The current inventory identifier set is:

```text
decisions union manifests union receipts union clears union reservations
```

It reports decision count, pending-decision count, invalid-current-record count,
and `decision_pending`. Any present current payload that fails typed,
versioned, canonical-byte, path, or cross-field validation is blocking.

## Typed current contracts

- Decision remains schema version 1.
- Completion receipt becomes schema version 3.
- Ownerless reservation becomes schema version 2.
- Clear receipt remains schema version 1.
- Git object IDs are exactly 40 or 64 lowercase hexadecimal characters.
- Provider-prefixed and undeclared fields are rejected by closed models and
  schemas.
- `OwnerlessCloseoutAdmission` remains a frozen, immutable, fact-only snapshot.
  It contains observed values; it owns no callables, runtime services, or
  dependency injection.

## Byte- and descriptor-exact observation

### Fixed Git execution

Every mandatory lifecycle Git observation uses the literal executable `git`, raw
byte stdout/stderr, `shell=False`, no `executable=` override, and an environment
with `GIT_OPTIONAL_LOCKS=0`. A non-zero exit, malformed output, unexpected
stderr, decode requirement, or observation exception is unverifiable and blocks.

Cleanliness includes:

- porcelain-v2 status including all untracked files;
- worktree diff bytes;
- staged/index diff bytes;
- exact untracked inventory bytes;
- rejection of every `assume-unchanged` or `skip-worktree` index entry.

No Git blob, patch, path, or worktree-list payload is decoded and encoded again
when exact bytes decide authority.

### Descriptor-bound worktree registration token

The synthetic `hash(branch, head, path)` incarnation is removed. Native
observation creates `GitWorktreeRegistrationToken` from descriptor-pinned facts:

- the target worktree directory identity;
- the target `.git` gitfile identity and exact bytes;
- the linked-worktree administration directory identity;
- the administration `gitdir` backlink identity and exact bytes;
- the exact registered path and administration path derived from those bytes.

All path components are opened from already bound directory descriptors with
`O_NOFOLLOW`; visible and descriptor identities must agree before and after the
read. The token is serialized deterministically for the existing
`lane_incarnation_id` decision field, while the complete typed token remains in
`OwnerlessGitFacts` and `OwnerlessCloseoutAdmission` for exact fence-held
comparison. Deleting and recreating a worktree at the same path, branch, and HEAD
must change the token and block the old decision.

### Chronicle and accepted-tree bytes

The Chronicle path is canonical, repository-relative, and beneath
`evidence/chronicle/`. Working bytes are read by walking from a pinned repository
root descriptor. Accepted bytes are read by exact Git object plumbing.

Before accepting the accepted-tree blob, ETHOS parses exactly one `ls-tree -z`
record and requires a regular blob mode (`100644` or `100755`). Symlink mode,
submodule mode, tree mode, duplicate records, absence, malformed output, and Git
failure block. Working bytes, accepted blob bytes, and the declared digest must
all match exactly. The required retirement disposition is then checked in UTF-8
text without replacing or normalizing bytes.

### Strict policy and state

An absent `.ethos/workspace.toml` uses the product default role policy. If that
file is present, invalid TOML, a missing or non-table `branch_roles` value, an
unknown field, or a field with the wrong raw type blocks ownerless admission.
The configured `work_branch_prefix` remains authoritative; no branch spelling is
hard-coded.

Lease and fence observation validates raw SQLite row and JSON types before
Pydantic construction. String, integer, boolean, sequence, timestamp, holder,
Claim, and digest fields cannot pass through truthy conversion or string
coercion. Damaged schema, payload, sidecar, lease, Claim binding, or fence state
is unverifiable, never equivalent to absence.

## Native admission boundary

Public API:

```text
OwnerlessCloseoutAdmission, frozen and slots-only fields:
  root, decision_path, decision, decision_bytes, decision_sha256,
  observation, registration_token, executor_ref, policy,
  accepted_branch, accepted_head, target_digest,
  target_binding_digest, existing_reservation

admit_ownerless_closeout(
  *, root: Path, decision_path: Path,
  decision: dict[str, Any], executor_ref: str
) -> OwnerlessCloseoutAdmission

reobserve_ownerless_closeout_under_fence(
  *, admission: OwnerlessCloseoutAdmission,
  fence: dict[str, object]
) -> OwnerlessCloseoutAdmission
```

Before the fence, admission proves:

1. canonical decision path, exact bytes, typed payload, and digest;
2. exact Chronicle path, accepted-tree mode, working bytes, accepted bytes,
   digest, and disposition;
3. strict configured branch-role policy and canonical executor reference;
4. exact accepted registration, branch, ref, live HEAD, and repository root;
5. exact target registration, branch, ref, live HEAD, descriptor token, and clean
   index/worktree/untracked state;
6. no current holder, lease, Claim, damaged state, or competing fence;
7. target HEAD is an accepted-HEAD ancestor, with a three-state ancestry result;
8. exact current-record integrity and exact retry reservation classification;
9. exact target, observation, and target-binding digests.

After acquiring the fence, ETHOS repeats the complete observation. The after-
fence probe runs from a `finally` boundary for every exception class. If the
fence cannot be proved identical both before and after re-observation, effect is
blocked and the original error cannot authorize cleanup.

## Effect, retry, recovery, and cleanup state machine

The execution order is fixed:

```text
completed-effect recovery precheck
-> exact pre-fence native admission and reservation classification
-> release/reset the old exact zero-effect fence and reservation, when classified
-> acquire a fresh exact fence
-> complete under-fence re-observation
-> persist typed reservation
-> no-force registered-worktree removal
-> verify accepted ref unchanged
-> delete exact target ref through CAS
-> verify ref, registration, path, state, decision, and fence postconditions
-> write immutable receipt
-> release exact fence through CAS
-> delete exact reservation
```

Completed-effect recovery validates the exact decision and Chronicle before
reconstructing or accepting a receipt; it runs before ordinary target worktree
observation because a completed effect has already removed that worktree.

A zero-effect retry may rebind only after exact pre-fence admission classifies
the same decision, executor, target, registration token, coordination facts, and
reservation as a zero-effect retry, the current accepted HEAD equals or descends
from the reserved accepted HEAD, and no worktree/ref effect occurred. Descendant
classification happens before ordinary competing-reservation rejection. ETHOS
then releases the old exact fence and reservation, acquires a fresh fence, and
performs the complete under-fence re-observation before persisting a fresh
reservation or starting effect.

Cleanup uses explicit phase and recovery state. The overloaded
`fence_acquired: bool` signal is removed. Exceptions before effect may release
only a provably owned fence with no durable effect reservation. Exceptions at or
after the effect boundary preserve visible reservation state and classify the
transition as partial or unknown. Receipt-present cleanup is effect-free and
keeps fence-CAS release before reservation deletion.

`OwnerlessCloseoutRuntime`, `ResolutionRuntime`, `_ownerless_runtime()`,
`_resolution_runtime()`, and callable/runtime dictionaries are deleted. Production
modules import concrete symbols from defining modules. Tests patch the consumer
module boundary instead of injecting a production callback bag.

## Preservation remains recovery package v2

Preservation is native and uses fixed Git plus Python `tarfile`; external `tar`
is not a mandatory lifecycle executable. Untracked members are walked from a
pinned source descriptor with `openat`/`O_NOFOLLOW`, preserved as raw bytes, and
captured through bounded-memory spooling. Parent-directory replacement, member
replacement, unsupported file types, symlink drift, and large-file races block.

The current candidate v2 contract is retained:

```text
repository.bundle
tracked.patch
index.patch
untracked.tar, when needed
manifest.json with package_format_version=v2,
  patch_sha256, index_patch_sha256, and archive digest
```

Descriptor hardening is a semantic port onto this v2 shape. It is not permission
to restore the older package writer or to drop staged-index recovery.

## Generic executable coupling

`system/coupling.toml` declares audit-root-bound mandatory lifecycle paths and
their allowed executables. For lane resolution the only declared external
executable is literal `git`; SQLite, JSON, schema, filesystem descriptors, and
`tarfile` are in-process native protocols.

A declaration-driven AST audit scans only those mandatory paths and blocks:

- an executable absent from the declaration;
- dynamic or computed `argv[0]`;
- a command string or `shell=True`;
- a non-`None` `executable=` override;
- a mandatory subprocess boundary outside the declared audit root.

Optional semantic-attestation, control-replacement, release-profile, and policy
adapters remain outside this mandatory-path audit unless separately declared.
The audit is generic; no permanent provider-name blacklist, source constant, or
special-case rule is added.

## Module and quality boundaries

- Every `__init__.py` contains only a docstring.
- Callers import from defining modules; no facade, alias, compatibility shell,
  `__getattr__`, or single-implementation Protocol is introduced.
- The `_observation.py` to `observation.py` rename is net-neutral module count.
  The layout gate is corrected only so existing-directory growth is reported
  when `current_count > previous_count`; 5-to-6 growth and burst rules remain
  blocking.
- `closeout/admission.py` stays at or below the repository logic soft limit.
- The enlarged lane-resolution record edge test is split by semantic concern
  rather than raising the code-size limit.
- Branch-owned Ruff debt (`EM101`, `TRY003`, `PLR0911`) is removed in source;
  `.config/checks/ruff/ratchet.toml` is not expanded.
- Module-layout, Ruff, code-size, no-compat, and import baselines may shrink only.

## Proof, archive, land, and stop conditions

Focused RED/GREEN evidence precedes each production slice. Full proof is bound to
one stable signed HEAD. Generic parity evidence is written and committed in the
admitted successor lane before executed proof.

Official OpenSpec archive changes HEAD, so archive validation and exact-HEAD proof
run again after archive. Land to candidate, accepted-root closeout, and local
publish readiness are separate transitions. Remote push is not authorized.

Mutation stops when any of these is true:

- candidate is not an ancestor of the successor HEAD;
- native refresh reports a real conflict;
- the successor would overwrite newer candidate truth, especially recovery
  package v2 and `index.patch`;
- current inventory, fence, reservation, decision, Chronicle, lease, Claim,
  policy, Git, descriptor, or ancestry state is unverifiable;
- the registration token changes at the same path/ref/HEAD;
- the fence differs before or after re-observation;
- branch-owned Ruff, module-layout, code-size, import, schema, coupling, residue,
  parity, Claim, OpenSpec, or proof gates remain gapped;
- candidate advances after proof and before land;
- archive HEAD has not received a fresh executed proof;
- lane ownership or exact absorption is insufficient for retirement.

## Rollback and housekeeping boundary

Before land, rollback is deletion of the successor only after its evidence has
been reviewed; the original lane remains the rollback carrier. After land,
rollback is a new governed Change. Historical records never regain current
authority automatically.

Housekeeping removes only task-owned successor/predecessor lanes after exact
absorption, task scratch, review packets, bytecode, caches, and temporary proof
artifacts. Foreign lanes, virtual environments, Git history, predecessor local
records, SQLite history, and IDE/session JSONL or database state remain untouched.
