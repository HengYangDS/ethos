# ETHOS

ETHOS is Evidence-backed Trust for Human-agent Operational Stewardship.

It is a reflexive, standards-compatible, agentic-native governance kernel for
deterministic repository change, evidence, release, and evolution.

## Command Plane

Daily workflow:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

Advanced workflow:

```bash
ethos adopt
ethos doctor
ethos campaign
ethos self
ethos quality
ethos report
```

Legacy public roots such as `wt`, `proof`, `mission`,
`skill-evolution`, and `agent-surface-contract` are retired. They may appear
only in archive, migration notes, or negative regression tests.

## Kernel

ETHOS reduces repository operation to one chain:

```text
Constitution -> Subject -> Commitment -> Change -> Evidence -> Chronicle -> Evolution
```

Packages are derived shells over that kernel. They do not create separate truth
centers.

## Packages

```text
packages/ethos/             thin CLI and UX composition
packages/ethos-kernel/      pure kernel and action graph algebra
packages/ethos-governance/  policy, proof, quality, docs, registry, attestation
packages/ethos-workspace/   lanes, local state, action runs, land, publish
packages/ethos-agent/       context packs, playbooks, MCP/ACP projections
packages/ethos-adopt/       profiles, project adoption, migration
```

## Development

```bash
uv run --group dev pytest
uv run --group dev ruff check .
PYTHONPATH=packages/ethos/src:packages/ethos-kernel/src:packages/ethos-governance/src:packages/ethos-workspace/src:packages/ethos-agent/src:packages/ethos-adopt/src \
  uv run --group dev python -m ethos.cli status --json
```
