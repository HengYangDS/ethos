# Proposal

## Why

An installed governor must provide a usable migration for repositories it already manages.
Retained authoring identities currently block that migration, leaving adopters dependent on
duplicated local governance that cannot safely be retired.

## What Changes

- Admit upgrade inputs before expensive preparation through the existing runtime scope owner.
- Provide native migration of retained authoring identities with exact source and destination
  bindings, preserving topic content, index intent and lane ownership.
- Qualify upgrade, rollback and renewed authoring against a real installed predecessor.
- Keep strict normal authoring rules; migration is a bounded transition, not a compatibility alias.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-transaction`: preserve retained authoring resources through a native identity migration.

## Impact

Existing lane, reference-transaction, Lease, OpenSpec and installation-acceptance owners.
No new state store, parallel task ledger, adopter controller or dependency.
Adopter business behavior and unrelated governance remain outside this Change.
