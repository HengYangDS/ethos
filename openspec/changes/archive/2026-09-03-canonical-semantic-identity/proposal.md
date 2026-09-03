## Why

ETHOS currently has two implementations that both claim to canonicalize JSON
before deriving semantic identity. The typed Commitment and Attestation path
uses the kernel's closed value grammar and UTF-16 key ordering, while the
generic digest path and several authority-bearing consumers use ordinary
`json.dumps(sort_keys=True)`. Equivalent meaning can therefore acquire
different bytes across entry paths, and the generic path can accept values the
semantic grammar rejects.

## What Changes

- Establish one kernel-owned canonical JSON byte projection for semantic
  identity, signature payloads, and admission digests.
- Make the generic semantic digest delegate to that byte projection, including
  closed-value validation, UTF-16 key ordering, UTF-8 encoding, and whitespace-
  free output.
- Migrate every currently identified JSON identity whose proposition is semantic
  equality or admission equality: transition inputs, proof-floor and control-
  replacement subjects, and independent-verification signed payloads. Delete
  their duplicate serialization helpers rather than preserving aliases.
- Remove projected RuleSet, compiled-policy, skill-registry, and source-budget
  inventory digests that have no identity-checking consumer; their typed content
  remains available without pretending that an unused checksum is authority.
- Explicitly retain raw-byte hashes, Git object identity, content-addressed
  carrier bytes, and human/display serialization under their native owners;
  they are not semantic JSON identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kernel`: Require every JSON value that participates in semantic identity,
  signature, or admission to use the same closed canonical byte projection,
  without mechanically conflating raw content hashes or display serialization.
- `contracts`: Retire the source-budget report's unconsumed inventory checksum
  obligation while preserving deterministic inventory and measurement facts.

## Impact

- Changes the semantic-kernel canonicalization helper and its focused tests.
- Removes the duplicate rule digest implementation, migrates its real proof-
  floor consumers, and deletes unconsumed checksum projections.
- Aligns independent-verification receipt digest and signature bytes with the
  same semantic owner, without treating the receipt as a new semantic root.
- Updates the product contract plus the kernel and contracts deltas; it does not
  restructure packages, migrate runtime manifests, alter Git object hashing, or
  normalize display JSON.

## Routing

- Product meaning remains in `docs/governance/product-design-contract.md`.
- This bounded implementation and its progress live only in this official
  OpenSpec Change.
- Physical module-layout convergence remains a later dependency-ordered batch;
  this Change first establishes the semantic owner it must project.
