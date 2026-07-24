## Context

ETHOS already owns the irreversible ownerless-retirement effect: it observes the
lane, stores the decision, acquires a SQLite fence that competes with lease
acquisition, persists a durable reservation, removes the registered worktree
without force, performs exact Git reference CAS, verifies postconditions, writes
an immutable receipt, and recovers crash windows. A host-side verifier was added
between observation and effect and its response fields were promoted into ETHOS
contracts. At the same time, current readers scan both the canonical records
directory and predecessor worktree artifact roots. The result is split authority,
provider vocabulary in kernel contracts, and historical records participating in
current effect decisions.

The cutover starts only when current inventory has no inflight or partial record,
the closeout-fence table is empty, and no reservation sidecar is present. Those
conditions were observed before this Change was created.

## Goals / Non-Goals

**Goals:**

- Make ownerless lane-resolution admission and effect self-contained inside
  ETHOS repository and local-state authority.
- Preserve one exact CAS, one exact binding, and one exact receipt path.
- Separate current records from immutable history without a data migration.
- Make invalid or pending current records visible and fail closed.
- Respect the existing configured Work Lane role and branch prefix.
- Keep modules small, concrete, and directly imported; every `__init__.py`
  remains declaration-only.
- Remove retired provider vocabulary from the current tracked tree and prevent
  undeclared external lifecycle executables generically.

**Non-Goals:**

- No compatibility alias, dual reader, dual writer, provider adapter, facade,
  single-implementation Protocol, or package-root export.
- No archive/freeze/tombstone migration, activation marker, migration journal,
  or destructive history cleanup.
- No process-table occupancy substitute. Repository safety is derived from Git
  registration, clean state, accepted ancestry, lease/Claim state, fence
  exclusion, exact CAS, and fresh observations.
- No workspace-key migration or Work Lane creation-policy change.

## Decisions

### 1. One non-destructive authority cut

Current authority moves to:

```text
<accepted>-records/recovery/lane-resolution-v2/
```

Predecessor history remains at:

```text
<accepted>-records/recovery/lane-resolution/
<registered-worktree>/build/artifacts/lane-resolution/
```

`current_record_root()` is the only root used by decide, apply, recovery,
receipt, clear, and current inventory. `historical_record_roots()` is an
independent read-only locator for explicit history inspection. There is no
fallback from current to history, and current clear never deletes history.

Alternative rejected: moving or copying records. It creates a migration
authority, risks changing evidence bytes, and is unnecessary while no effect is
in flight.

### 2. Provider-neutral typed records

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

`OwnerlessCloseoutReservation` is the single schema-version-2 typed owner of
reservation shape and phase/recovery invariants. `records/core.py` delegates to
that model instead of maintaining a second handwritten field set. Clear receipts
carry `schema_version = 1`. Decision version 1 remains unchanged because its
meaning does not change.

Alternative rejected: retaining legacy fields or unversioned current readers.
That would keep the retired provider authoritative and make malformed current
payloads indistinguishable from history.

### 3. Native admission at the effect boundary

`closeout/admission.py` validates, in order:

1. exact canonical decision bytes and decision digest;
2. Chronicle existence, disposition, and digest;
3. configured Work Lane role rather than a hard-coded branch prefix;
4. exact registered worktree path, HEAD, and incarnation;
5. clean, ownerless state with no holder, lease, or Claim;
6. target HEAD ancestry under the current accepted HEAD;
7. canonical executor reference and target/target-binding digests;
8. the same complete observation after the SQLite fence is acquired.

Any mismatch returns a stable gap before Git or worktree effect. The executor
then reuses the existing no-force removal, accepted-ref no-op verification,
target-ref exact delete CAS, three-state probes, durable reservation, and receipt
cleanup order.

Alternative rejected: recreating the host verifier response internally. Echoed
tree/layout/coordination fields add a second wire contract without adding a new
repository invariant.

### 4. Current inventory is complete and strict

Inventory enumerates the union of decision, manifest, receipt, clear, and
reservation identifiers. It reports `decision_count`,
`pending_decision_count`, `invalid_current_record_count`, and the
`decision_pending` state. A payload present in the current root that cannot be
validated is a blocking integrity record; it is never skipped.

Alternative rejected: treating parse failure as absence. That converts damaged
authority into apparent safety.

### 5. Existing configured Work Lane role is authoritative

Native admission consumes the existing branch-role policy and its configured
`work_branch_prefix`. It does not rename a workspace key, change lane-start
behavior, rename existing registered worktrees, or infer authority from a
directory spelling.

### 6. Generic coupling prevention

Coupling audit compares observed lifecycle executable bindings with declared
bindings in `system/coupling.toml`. The Work Lane lifecycle contract admits Git,
ETHOS state/SQLite, and native JSON/schema operations. An undeclared mandatory
external command is blocking. The check is provider-neutral and does not retain
a permanent special-case token for the retired dependency.

### 7. Concrete module boundaries

- `ethos_core/contracts/resolution/closeout.py`: receipt binding and typed
  reservation contracts.
- `resolution/records/roots.py`: current and historical root location only.
- `resolution/records/reservations.py`: reservation persistence and transition
  helpers using the typed model.
- `resolution/closeout/admission.py`: native pre-effect validation.
- Existing effect, retry, recovery, cleanup, state, and receipt modules retain
  their current distinct responsibilities and import defining modules directly.

The retired adapter package is deleted. No `__init__.py` exports names.

## Risks / Trade-offs

- **Current-root cut hides predecessor records from ordinary inventory** → Keep
  them in place and expose only an explicit opaque history view if required;
  document that history never authorizes current effect.
- **Contract cut rejects predecessor payloads** → Current root starts empty and
  strict; predecessor payloads are never parsed as current.
- **Accepted HEAD advances during zero-effect retry** → Permit rebinding only
  when the target and decision are unchanged, no effect occurred, and the new
  accepted HEAD descends from the reserved accepted HEAD.
- **Module growth exceeds repository limits** → Move roots, reservations, and
  admission into concrete semantic modules; do not raise layout or size limits.
- **Vocabulary cleanup could erase history meaning** → Replace only the retired
  token with neutral repository-role wording, retain dates, decisions, digests,
  limitations, and chronology, then rebind Claim digests.
- **Generic coupling detection overreaches optional adapters** → Apply it only
  to mandatory lifecycle execution paths; optional configured attestation and
  policy adapters remain outside this Change.

## Migration Plan

1. Establish and strictly validate this successor Change, Claim, Chronicle,
   design, and implementation plan.
2. Add failing contract/root/inventory tests, then implement the versioned
   current root and typed records.
3. Add failing native-admission and configured-role tests, then reconnect the
   existing fence/reservation/recovery/CAS effect path and delete the external
   adapter.
4. Add failing generic coupling and provider-neutral residue tests, then update
   schemas, docs, canonical spec, Claim, Chronicle, and
   historical tracked vocabulary.
5. Run focused and complete gates, generic shadow parity, and exact-HEAD proof.
6. Officially archive the Change, update the Claim carrier and Chronicle, rerun
   proof, land to candidate, perform accepted-root closeout, and report local
   publish readiness without pushing.
7. Retire only task-owned lanes and predecessor mistake lanes through native
   closeout. If absorption cannot be proved, use Chronicle-bound preserve-retire.

Rollback before land is branch deletion after evidence review. After land, the
rollback is a new governed Change; predecessor records remain available as
history but never regain automatic current authority.

## Open Questions

None. The authority, migration, contract, module, and closeout boundaries are
fully decided for implementation.
