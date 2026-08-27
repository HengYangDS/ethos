## Context

The semantic models already own validation and identity. `_canonical_set` also
requires pre-sorted input, although equivalent members can be normalized after
duplicate and conflict checks.

## Decision

The existing contract remains the only owner. Its collection helper validates
unique identities and returns members sorted by the same identity key.
Every model validator continues to enforce its field-specific membership,
duplicate, reference, and conflict rules before or around that helper.

Canonical JSON and digests therefore operate only on normalized typed values.
Input permutations have one value and one identity. A JSON reader for an
already-issued content-addressed envelope may still require exact canonical
bytes; that storage-boundary check is separate from general model validation.

## Deletion

Remove the order-invalid error, rejection regression, and any current contract
language requiring callers to pre-sort semantic collections. Do not add a
formatter, second parser, migration branch, or fallback.
