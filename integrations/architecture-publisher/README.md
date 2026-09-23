# ETHOS Architecture Publisher integration

`@architecture-publisher/ethos` is the sole mutable ETHOS-owned adapter and
Edition for Architecture Publisher. It translates one explicitly selected ETHOS
terminal-architecture projection into Architecture Publisher public contracts.

Exports:

```text
@architecture-publisher/ethos/provider
@architecture-publisher/ethos/adapter
@architecture-publisher/ethos/edition
@architecture-publisher/ethos/runtime
```

The Provider export exposes only `materializeEditionProvider`. Publisher admits
its standard request and binds the installed package and inputs before execution.
One `edition` JSON input selects exact source members, projection digest,
renderer-neutral Edition selection and optional evolution. The reply contains
only Source Bundle members, Claim Model, Edition and optional evolution.
Existing source and Edition authors remain the semantic owners; Publisher owns
materialization validation and every later-stage effect.

The remaining exports are migration incumbents, not the terminal Provider
boundary. Retire them and their generic mechanics only after conformance,
semantic and artifact parity or a reviewed successor, relocation and rollback.

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
