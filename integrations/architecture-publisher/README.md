# ETHOS Architecture Publisher integration

`@architecture-publisher/ethos` is the sole mutable ETHOS-owned adapter and
Edition for Architecture Publisher. It translates one explicitly selected ETHOS
terminal-architecture projection into Architecture Publisher public contracts.

Exports:

```text
@architecture-publisher/ethos/adapter
@architecture-publisher/ethos/edition
@architecture-publisher/ethos/runtime
```

The package is an independently installable, optional downstream consumer of
`architecture-publisher`. It exposes input-driven JavaScript APIs rather than an
ETHOS command or a second command plane. Absence of this package does not alter
ordinary ETHOS governance, proof, installation, or release behavior.

ETHOS retains sole authority over repository intent, Commitments, Work Lanes,
proof, CAS effects, Attestations, and acceptance. This package may project those
facts but cannot authorize, reinterpret, or mutate them. Runtime inputs must be
explicit and portable; installed execution must not discover an adjacent
checkout or user configuration.

`migration-baseline.json` identifies the exact one-time Publisher staging bytes
and ETHOS projection used to establish source ownership. It is migration
evidence, not current acceptance or publication proof. The Publisher staging
copy may be removed only after independently packed parity or an explicitly
reviewed semantic successor is proven.
