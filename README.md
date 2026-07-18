# ETHOS

ETHOS is Evidence-grounded Trust for Human-Agent Operational Stewardship.

It gives a Git repository a safe operating loop for human-agent change: inspect
where you are, plan the required proof, run that proof, land through a controlled
review path, and publish only when local and hosted evidence are separated.

ETHOS does not take over your domain model, CI provider, assistant host, or issue
tracker. Those systems stay adapters or projections. Repository source, tests,
schemas, docs, evidence, and promoted decisions remain the truth.

## Isomorphic Governance

ETHOS governs the ETHOS product repository and adopted repositories through the
same kernel: authority, subject, commitment, change, evidence, claim, and chronicle.
Product and adopter work differ by profiles and adapters, not by separate command
planes or private truth stores. This is not product cloning: each governed
repository keeps its domain model, provider surfaces, and local shape while ETHOS
applies one evidence-bound transition loop.

The same commands answer the same transition questions in every governed
repository: where am I, what may mutate, which proof is required, can this land,
and what publication boundary remains. Repository truth stays in source, tests,
schemas, docs, evidence, and promoted decisions; profiles tune checks and proof
depth, while adapters project local providers without becoming truth stores.

## First Hour

The first hour is deliberately small. Start with a first-glance orientation,
then run the transition loop:

```text
status -> plan -> prove -> land -> publish
```

```bash
ethos orient
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

`ethos orient` is read-only UX for humans and agents: where am I, what can I do,
who else is present, what remains gapped, and what runs next. It projects
`status` and `report`; it is not a transition verb and does not mint repository
truth.

report is a read-only scorecard. It shows the payoff after the loop, but
it is not another transition verb:

```bash
ethos report
```

Start read-only. Choose an adoption profile, review the planned files with a
dry run, apply only when the generated file list and rollback path are clear,
then use the five-command loop above.

## Human And Agent Discovery

Use one discovery path, then branch by audience:

```text
README / docs index / AGENTS.md -> ethos orient -> status -> plan -> prove -> land -> publish
```

- Humans start from this README, then the [docs index](docs/index.md) and
  [quickstart](docs/start/quickstart.md).
- Agents start from [AGENTS.md](AGENTS.md), load the matching rule and skill,
  then run `ethos orient --json` before planning mutation.
- Both treat `ethos orient` as a reader view: it makes role, capability, foreign
  Work Lanes, unbound Work Lane refs, gaps, and next commands visible without
  minting truth.
- Foreign Work Lanes and unbound Work Lane refs are coordination signals.
  Visibility is collaboration, not authority; write, land, retire, or cleanup
  requires owner handoff or maintainer break-glass evidence.

## Kernel

ETHOS product truth is judged from one source and projected through one canonical
chain:

```text
Authority -> Subject -> Commitment -> Change -> Evidence -> Claim -> Chronicle
```

`Authority` anchors product decisions. `Subject` names the
governed object. `Commitment` collects contracts, policies, specs, and decisions.
`Change` owns the lifecycle. `Evidence` carries proof material. `Claim` binds
evidence and does not own lifecycle state. `Chronicle` records judged history,
decisions, supersession, and current-state movement.

## Packages

```text
packages/ethos-core/        pure kernel, contracts, and quality semantics
packages/ethos/             runtime, CLI, repository orchestration, adapters, assistants, and testing
distributions/npm/          npm launcher adapter
```

These packages are the current product topology. The canonical ontology is
defined in `docs/architecture/package-ontology.md`.

The npm package is a thin launcher over the Python command plane:

```bash
npm run ethos -- --version
```

## Maintainer Reference

ETHOS can inspect and evolve the governed repository through
maintainer/reference commands:

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
tools/ci/scripts/run-python-tests.sh
tools/ci/scripts/run-python-lint.sh
uv run --package ethos ethos orient --json
uv run --package ethos ethos status --json
uv run --package ethos ethos report --json
```
