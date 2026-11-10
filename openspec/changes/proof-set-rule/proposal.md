# Proposal

## Why

The default proof is meant to be the fast offline source floor; the docs say so
(`docs/architecture/gate-runner.md`). Nothing enforces it. A registry, ETHOS's or an adopter's, can
put a networked or package gate into `default`, directly or through a dependency, and the narrower
proof then silently needs the network or a build. Measured at `d8760f044`: ETHOS's `default` and its
dependency closure run 15 gates, all offline and none a package gate.

## What Changes

- Validating a gate registry refuses a `default` proof set that differs from `full` and whose
  dependency closure holds a gate that is not offline or whose kind is `package`.
- A registry whose `default` equals `full` is unaffected, as every governed repository's is today:
  none declares `proof_sets`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a narrower default proof holds only offline source checks.

## Impact

- `src/ethos/contracts/gates.py` and the registry tests; `CHANGELOG.md`.
- A registry that breaks the rule fails to load with the new message; no current registry does.
