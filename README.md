# ETHOS

<p align="center">
  <img src="assets/brand/ethos-lockup-dark.svg" alt="ETHOS" width="520">
</p>

<p align="center">
  <em>Evidence-grounded Trust for Human-Agent Operational Stewardship</em>
</p>

ETHOS is Evidence-grounded Trust for Human-Agent Operational Stewardship.

See the [Brand Kit](docs/reference/brand-kit.md) for repository-owned public identity and presentation assets.

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

The first hour is deliberately small. Start with the single bounded reader,
then run the lifecycle loop:

status is the read-only readiness view.

```text
status -> plan -> prove -> land -> publish
```

```bash
ethos status
ethos plan
ethos prove
ethos land
ethos publish
```

`ethos status` is the single bounded reader for current repository facts,
authority, gaps, coordination, and the next action. It does not mint repository
truth.

Start read-only with `ethos adopt --json`. Review the exact one-file binding
plan, apply only when conflicts are empty and rollback is clear, then use the
five-command loop above.

## Human And Agent Discovery

Use one discovery path, then branch by audience:

```text
README / docs index / AGENTS.md -> status -> plan -> prove -> land -> publish
```

- Humans start from this README, then the [docs index](docs/index.md) and
  [quickstart](docs/start/quickstart.md).
- Agents start from [AGENTS.md](AGENTS.md), load the matching rule and skill,
  then run `ethos status --json` before planning mutation.
- Both treat `ethos status` as a reader view: it makes role, capability, foreign
  Work Lanes, unbound Work Lane refs, gaps, and next commands visible without
  minting truth.
- Foreign Work Lanes and unbound Work Lane refs are coordination signals.
  Visibility is collaboration, not authority; write, land, retire, or cleanup
  requires owner handoff or maintainer break-glass evidence.

## Kernel

ETHOS product truth is judged from one source and projected through one canonical
chain:

```text
ChangeContract + Attestation -> RepositoryFacts -> PlanIR
```

`ChangeContract` owns immutable intent and authority references. `Attestation`
binds observations and judgments to evidence. `RepositoryFacts` is re-observed;
`PlanIR` is transient. No parallel subject, commitment, evidence, claim, or
chronicle model owns truth.

## Product Shape

```text
src/ethos/          one cohesive Python product package
distributions/npm/  thin npm launcher adapter
```

The package contains the semantic kernel, contracts, command plane, repository
orchestration, adapters, and projections. Internal module boundaries protect
meaning; a second distribution package is not needed to express them.

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
ethos prove --gate docs-registry --json
ethos prove --json
ethos publish --json
ethos assistants mcp-manifest
```

The same evidence, docs, schema, and proof-gate rules used for adopter
repositories apply to ETHOS product changes.

## Release Readiness

GitLab-visible project governance is tracked in `LICENSE`, `CONTRIBUTING.md`,
`CHANGELOG.md`, `.gitlab-ci.yml`, and GitLab templates. Use
`ethos prove --full --execute --json` and `ethos publish --json` before publishing.

## Development

```bash
tools/ci/scripts/run-python-tests.sh
tools/ci/scripts/run-python-lint.sh
uv run ethos status --json
uv run ethos plan --changed --json
uv run ethos prove --json
```
