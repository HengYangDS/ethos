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
ethos assistants
ethos report
```

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

## Reflexive Governance

ETHOS can inspect and evolve itself:

```bash
ethos self audit
ethos campaign hypotheses
ethos quality docs-registry
ethos quality provenance
ethos quality release
ethos assistants mcp-manifest
```

The same evidence, docs, schema, and command registry rules used for adopter
repositories apply to ETHOS product changes.

## Release Readiness

GitLab-visible project governance is tracked in `LICENSE`, `CONTRIBUTING.md`,
`CHANGELOG.md`, `.gitlab-ci.yml`, and GitLab templates. Use
`ethos quality release --json` before publishing.

## Development

```bash
uv run --group dev pytest
uv run --group dev ruff check .
uv run --package ethos ethos status --json
uv run --package ethos ethos report --json
```
