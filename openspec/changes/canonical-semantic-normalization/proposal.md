## Why

Commitment and Attestation collections currently reject otherwise valid values
when callers present members in a non-canonical physical order. Ordering is an
identity projection concern, not semantic validity, and the rejection repeatedly
transfers deterministic serialization work to humans and agents.

## What Changes

- Validate collection members, duplicates, identities, and references without
  treating caller order as authority.
- Normalize unordered semantic collections in the typed contract owner before
  canonical JSON, digest, signature, or equality is derived.
- Delete the retired collection-order error and its order-as-validity tests and
  documentation.
- Keep exact canonical-byte rejection only at readers whose contract explicitly
  requires an already content-addressed canonical JSON carrier.

## Out of Scope

No formatter command, compatibility reader, alternate schema, state machine, or
historical archive rewrite is introduced.
