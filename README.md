# ETHOS

ETHOS is Evidence-grounded Trust for Human-Agent Operational Stewardship.

It gives a Git repository a safe operating loop for human-agent change: inspect
where you are, plan the required proof, run that proof, land through a controlled
review path, and publish only when local and hosted evidence are separated.

ETHOS does not take over your domain model, CI provider, assistant host, or issue
tracker. Those systems stay adapters or projections. Repository source, tests,
schemas, docs, evidence, and promoted decisions remain the truth.

## First Hour

The first hour is deliberately small:

```text
status -> plan -> prove -> land -> publish
```

Daily workflow:

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

report is a read-only scorecard. It shows the payoff after the loop, but it is
not another transition verb:

```bash
ethos report
```

Start read-only. Choose an adoption profile, review the planned files with a
dry run, apply only when the generated file list and rollback path are clear,
then use the five-command loop above.

## Kernel

ETHOS product truth is judged from one source and projected through one canonical
chain:

```text
JudgmentSource -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

`JudgmentSource` is the authority for product decisions. `Subject` names the
governed object. `Commitment` collects contracts, policies, specs, and decisions.
`Change` owns the lifecycle. `Evidence` carries proof material. `Claim` binds
evidence and does not own lifecycle state. `Chronicle` records judged history,
decisions, supersession, and current-state movement.

## Packages

```text
packages/ethos/             thin CLI and UX composition
packages/ethos-core/        pure kernel and action graph algebra
packages/ethos-contracts/   provider-neutral contracts and schemas
packages/ethos-repository/  repository lifecycle, governance, proof, quality
packages/ethos-assistants/  context packs, playbooks, MCP/ACP projections
packages/ethos-adapters/    Git, SQLite, process, OpenSpec, and distribution adapters
packages/ethos-test/        conformance, parity, and sample proof fixtures
distributions/npm/          npm launcher adapter
```

These packages are the current product topology. The canonical ontology is
defined in `docs/architecture/package-ontology.md`.

The npm package is a thin launcher over the Python command plane:

```bash
npm run ethos -- --version
```

## Maintainer Reference

ETHOS can inspect and evolve itself through maintainer/reference commands:

```bash
ethos audit
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
