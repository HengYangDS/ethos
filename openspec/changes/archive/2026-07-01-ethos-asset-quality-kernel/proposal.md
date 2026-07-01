## Why

ETHOS already exposes `ethos quality ...` commands, but the product ontology
does not contain a quality family. As a result, quality, determinism, docs
quality, proof policy, and gate descriptors are split across repository
lifecycle and CLI code.

## What Changes

- Add `ethos-quality` as a first-class product package and OpenSpec family.
- Move quality asset policy, gate descriptors, docs profile, and proof lattice
  into provider-neutral product semantics.
- Tighten schemas so gate and proof outputs carry trust-bearing classification.
- Move reference-adopter parity instance data out of provider-neutral
  contracts.
- Extend docs quality checks for taxonomy states and nested command examples.

## Impact

- Affected code: `packages/ethos-quality`, `packages/ethos-repository`,
  `packages/ethos-contracts`, `packages/ethos`, and `schemas/ethos`.
- Affected docs: package ontology, command plane, docs registry, evidence, and
  OpenSpec canonical specs.
- Affected behavior: `ethos quality ...` reports become semantic product
  outputs rather than incidental CLI wrappers.
