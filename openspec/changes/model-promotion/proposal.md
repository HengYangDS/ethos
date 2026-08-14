## Why

ETHOS cannot yet guarantee that rapidly arriving human or agent intent is both
preserved and kept outside an active Change until normatively adopted. Prior
attempts accumulated Claims, Chronicle, evolution ledgers, Campaign state,
shared inbox views, and oversized Changes. Those carriers either lost intent,
duplicated authority, or prevented closure.

A second defect makes the same Commitment bytes mean different things under
different package versions: schema v1 changed identity-bearing defaults without
changing its version. A Lease can therefore bind a digest that another runtime
cannot reproduce.

This Change promotes the smallest model that closes both gaps. Commitment and
Attestation remain the only durable semantic roots. One Git-native Attestation
set preserves concurrent occurrences without expanding an active Change.
Selection remains non-authorizing; only a schema-v2 successor Commitment adopts
intent.

## What Changes

- Replace Commitment v1 with explicit schema v2. Version 2 freezes fields,
  normalization, canonical projection, digest domain, and empty values; it
  forbids contextual aliases and reusable permissions.
- Add predecessor Commitment digests, selected Attestation identities, typed
  dependencies, hypotheses, falsifiers, and experiment protocols.
- Replace Attestation v1 with schema v2: open predicate, discriminated payload,
  composable canonical relations, exact bindings, and invariant
  `mints_authority=false`. Unknown kinds round-trip but never authorize effects.
- Replace current Attestation authorities with one Git-native set at
  `refs/ethos/attestations-set`. Its deterministic parentless root contains
  hash-sharded canonical members. Exact-CAS set union preserves concurrency;
  membership proves preservation only.
- Add one narrow record/query projection over that set. It owns no workflow,
  selection policy, lifecycle, or task state.
- Make selection an Attestation disposition: semantic owner, absence reason,
  contradiction, or model gap. Normative adoption requires a successor
  Commitment, one OpenSpec Change, one writable lane generation, and one task
  authority.
- Remove current Claim, Chronicle, evolution-ledger, Campaign, shared-inbox,
  reusable-permission, and duplicate Attestation-store authority. Historical
  tracked bytes remain inert and never enter a current verdict.
- Extend the existing exact Commitment rebind operation with one destructive
  v1-to-v2 bootstrap. It treats the old Lease tuple as opaque CAS input,
  validates only the new v2 carrier, advances one generation, and emits an
  Attestation. No general v1 reader remains after cutover.

## Capabilities

### Modified Capabilities

- `kernel`: immutable versioned identity and open fail-closed input.
- `contracts`: Commitment v2, Attestation v2, typed lineage and experiment
  values, and packaged golden vectors.
- `adapters`: deterministic Attestation-set observation and CAS union.
- `repository-governance`: bounded successor adoption and removal of parallel
  intent/progress authority.
- `command-plane`: minimal Attestation record/query and one-shot Commitment v2
  bootstrap through the existing rebind family.

### Removed Capabilities

- Commitment v1 current mutation, reusable Commitment permissions, active Claim
  and Chronicle authority, evolution ledger, Campaign lifecycle/progress,
  shared-inbox truth, and multiple current Attestation stores.

## Out Of Scope

This Change does not migrate refresh, land, release transitions, retirement,
history replacement, hooks/runtime installation, proof execution, or provider
publication. It does not modify AIGW, Proxy, or foreign lanes. Remote protection
and replication of the Attestation set remain unverified successor work.
