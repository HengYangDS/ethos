## Why

ETHOS must become the external product truth for repository governance instead
of remaining a reference adopter-embedded implementation with product-like behavior. The
previous state had a good design contract, but the physical package homes,
capability parity ledger, fast verification path, and adopter shadow-parity
control plane were still incomplete.

## What Changes

- Add the target product packages: `ethos-core`, `ethos-contracts`,
  `ethos-repository`, `ethos-assistants`, `ethos-adapters`, and `ethos-test`.
- Keep migration-host packages as compatibility/migration sources while target
  homes become real buildable packages.
- Add executable capability parity commands under `ethos parity ...`.
- Add shallow/deep self-audit modes so daily `prove` and `report` stay fast
  while official OpenSpec validation remains available as a deep gate.
- Add in-process ETHOS gate execution for internal JSON gates.
- Add architecture tests preventing provider execution and adopter terms from
  leaking into semantic product packages.

## Capabilities

### Modified Capabilities

- `ethos-kernel`
- `ethos-governance`
- `ethos-workspace`

## Impact

Affected areas include package topology, CLI command surface, self-governance,
proof/report performance, parity governance, tests, docs, and build metadata.
