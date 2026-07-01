# Design: Product Migration Closure

## Boundary

The external ETHOS repository is the product truth. Historical in-product
migration hosts are not fallback mechanisms; fallback belongs to adopters such
as alphasim-dmgr through explicit backend selection and shadow parity evidence.

## Package Topology

The product topology is fixed to:

```text
ethos-core
ethos-contracts
ethos-repository
ethos-assistants
ethos-adapters
ethos
ethos-test
```

Non-Python distribution launchers live outside the Python package ontology:

```text
distributions/npm
```

## Dependency Direction

`ethos-repository` owns lifecycle semantics, not provider execution. It may
accept provider-neutral reports supplied by callers, but it must not import
`ethos-adapters`. The CLI composes repository semantics with provider adapters
for deep checks such as official OpenSpec validation.

## OpenSpec

Canonical specs and active deltas use the target MECE families. Completed
changes are archived through the official OpenSpec CLI with spec syncing skipped
when canonical specs were already updated in this batch.

## Evidence

Runtime state and generated build artifacts remain non-truth. Durable parity
closure uses tracked evidence under `docs/evidence/parity/`, claims bind to
dated evidence by SHA-256, and final proof output is produced through the ETHOS
command plane.
