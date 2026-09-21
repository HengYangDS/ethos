## Why

The live ETHOS Architecture Publisher adapter and Edition still reside in the
publisher repository as migration staging. That leaves ETHOS meaning under a
second mutable owner and makes architecture evolution depend on a repository
that must not govern ETHOS intent, Work Lanes, proof, CAS effects, or acceptance.

## What Changes

- Add one source-owned `@architecture-publisher/ethos` integration package below
  `integrations/architecture-publisher`.
- Consume the existing exact ETHOS terminal-architecture projection and emit only
  Architecture Publisher public values and artifacts.
- Keep the integration free of ETHOS mutation, Commitment compilation, Lane
  control, proof minting, CAS effects, and acceptance authority.
- Prove installed, relocated, offline behavior against an exact independently
  packed Architecture Publisher core.
- Bind migration parity to exact source, package, Candidate, static, and
  interactive identities; require explicit review for any semantic successor.
- Hand the verified source-owned package identity back to the Publisher change so
  its temporary mutable `migration/ethos` copy can be removed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: add the bounded source-owned Architecture Publisher adapter and
  Edition boundary for ETHOS.

## Impact

The change adds one optional JavaScript integration package, its native tests,
formatting coverage, package metadata, and exact migration evidence. It does not
change the ETHOS command plane, Python kernel, repository authority, release
roles, or accepted terminal architecture source projection.
