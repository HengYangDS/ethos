---
subject: ethos:native-lane-resolution-authority-design-20260724
role: plan
state: active
relations:
  derives_from: native-lane-resolution-authority
---

# Native Lane Resolution Authority Design

Status: approved for implementation.

Purpose: define the self-contained ETHOS authority, record, admission, recovery,
module, history, and coupling boundaries for clean ownerless Work Lane
retirement.

See also: [Implementation Plan](native-lane-resolution-authority-implementation-plan-20260724.md),
[Product Design Contract](../governance/product-design-contract.md), and
[Command Plane](../reference/command-plane.md).

## Decision

ETHOS owns the complete Work Lane lifecycle. Clean ownerless retirement uses one
native chain:

```text
decision and Chronicle snapshot
-> configured-role and exact Git/worktree observation
-> ownerless coordination and accepted-ancestry admission
-> SQLite fence
-> complete re-observation
-> durable typed reservation
-> no-force worktree removal and exact Git CAS
-> postconditions
-> immutable receipt
-> ordered cleanup
```

No host control plane, provider response, compatibility shim, or historical
record root participates in current authority.

## Authority boundaries

| Concern | Owner |
| --- | --- |
| Branch role and accepted policy | ETHOS repository configuration |
| Worktree path, HEAD, incarnation, ref and ancestry | Git observation |
| Lease, Claim and effect exclusion | ETHOS local state and SQLite fence |
| Decision, reservation, receipt and clear records | Versioned ETHOS current record root |
| Historical records | Opaque read-only history, never current effect authority |
| Irreversible effect | ETHOS no-force worktree and exact Git CAS adapter |
| Completion claim | Postcondition-bound immutable receipt and Chronicle |

## Record topology

```text
current:  <accepted>-records/recovery/lane-resolution-v2/
history:  <accepted>-records/recovery/lane-resolution/
          <worktree>/build/artifacts/lane-resolution/
```

Current commands use only `current_record_root()`. An explicit history reader may
use `historical_record_roots()`, but it cannot clear records, resolve conflicts,
recover effects, or mint decisions.

## Contract topology

- Decision remains version 1.
- Completion receipt becomes version 3.
- Ownerless reservation becomes typed version 2.
- Clear receipt becomes version 1.
- Git object IDs accept exactly 40 or 64 lowercase hexadecimal characters.
- Provider-prefixed or extra fields are rejected by closed models and schemas.

## Module topology

```text
ethos_core/contracts/resolution/closeout.py
  typed ownerless binding and reservation contracts

ethos/adapters/mutation/resolution/records/roots.py
  current and historical root location

ethos/adapters/mutation/resolution/records/reservations.py
  reservation persistence and transitions

ethos/adapters/mutation/resolution/closeout/admission.py
  native pre-effect validation and fence-held re-observation
```

Existing effect, retry, recovery, cleanup, receipt, state, and Git CAS modules
remain concrete owners. The retired adapter package is deleted. All callers
import from defining modules. Every `__init__.py` contains only a module
docstring.

## Admission invariants

Before effect and again after fencing, ETHOS proves:

1. canonical decision bytes and digest;
2. Chronicle path, digest, and disposition;
3. configured Work Lane role;
4. exact Git registration, path, HEAD, and incarnation;
5. clean ownerless state with no holder, lease, or Claim;
6. target HEAD is an accepted-HEAD ancestor;
7. exact executor, target, and target-binding digests;
8. no conflicting current reservation or invalid current record.

The existing effect path then preserves accepted-ref verification, target-ref
compare-and-delete, no-force removal, three-state inspection, visible crash
recovery, receipt-first cleanup, and exact fence release ordering.

## Inventory invariants

Current inventory uses:

```text
decisions union manifests union receipts union clears union reservations
```

It reports decision count, pending decision count, invalid current record count,
and `decision_pending`. Invalid current bytes are blocking. Predecessor records
are not current inventory input.

## Configured role and coupling policy

Native admission uses the existing configured `work_branch_prefix` and exact
Git registration. This Change does not rename workspace keys, change lane-start
behavior, or rename existing registered worktrees.

The coupling gate discovers mandatory lifecycle executable bindings and compares
them with `system/coupling.toml`. Git, ETHOS SQLite/state, and native JSON/schema
are declared. An undeclared external executable blocks proof. Optional unrelated
attestation and policy adapters remain explicitly configurable.

## History and cleanup boundary

The current tracked tree removes retired provider vocabulary even from Claims,
Chronicle, and archived OpenSpec carriers, but preserves dates, actions, evidence
digests, limitations, and chronology using neutral repository-role terms. Git
history and local predecessor receipts are untouched.
