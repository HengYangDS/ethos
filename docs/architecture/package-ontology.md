---
subject: ethos:target-package-ontology
role: decision
state: canonical
relations:
  canonical_for: target product package topology
---

# Package Ontology

The current packages in this repository are migration hosts. The target Python
product package ontology is:

```text
packages/ethos-core
packages/ethos-contracts
packages/ethos-repository
packages/ethos-assistants
packages/ethos-adapters
packages/ethos
packages/ethos-test
```

Non-Python distribution adapters do not belong to the Python product package
ontology. The Python product package ontology is limited to Python packages.
Distribution adapters use a separate layout:

```text
distributions/npm
distributions/homebrew
distributions/docker
distributions/github-action
distributions/gitlab-component
```

## Target Packages

### `ethos-core`

Pure kernel algebra. Owns Constitution, Subject, Contract, IR, Transition,
Inscription, Evidence, Chronicle, Evolution, action graph primitives, state
machine primitives, and result envelope primitives.

Forbidden: Git, OpenSpec, MCP, SQLite implementation, CLI parsing, pytest, nox,
Ruff, GitHub, GitLab, npm, dmgr, alphasim, and adopter-specific semantics.

### `ethos-contracts`

Provider-neutral contracts. Owns JSON Schema, TOML config schema, public result
schema, adapter interfaces, attestation envelope contracts, evidence contracts,
command registry contracts, assistant boundary contracts, and package ontology
contracts.

Forbidden: provider-specific execution.

### `ethos-repository`

Repository operation lifecycle semantics. Owns status, plan, prove, land,
publish, intake, campaign, quality and determinism semantics, command surface
semantics, evidence freshness semantics, local state logical model, and
workspace/lane logical model.

It answers one question: how one human-agent repository change is planned,
proved, landed, published, remembered, and evolved.

It must not shell out to providers directly. Provider work is delegated through
`ethos-adapters`.

### `ethos-assistants`

Assistant-facing repository operation boundary. Owns Playbooks, assistant
surfaces, method packs, context providers, projection classification, truth
boundaries, changed-scope routing to playbooks, and assistant doctor models.

It is not named `ethos-agent` because ETHOS does not implement an agent.

### `ethos-adapters`

Provider-specific integrations. Owns adapters for Git, SQLite, official
OpenSpec, Backlog, GitHub, GitLab, MCP, ACP, Superpowers detection, Dagger,
Pants, Bazel, Nx, SLSA, in-toto, Sigstore, pre-commit, Ruff, pytest, nox, pixi,
and hosted CI.

Adapters observe, execute, translate, and bind evidence. They do not own
product semantics.

### `ethos`

Public CLI surface. Owns cyclopts command tree, UX composition, human-readable
rendering, and JSON output routing.

The CLI must remain a thin shell and must not become the semantic center.

### `ethos-test`

Conformance, parity, and proof host. Owns conformance fixtures, sample
repositories, golden JSON outputs, adapter contract tests, schema compatibility
tests, migration replay fixtures, and shadow parity harnesses.

## Migration Hosts

Current packages such as `ethos-governance`, `ethos-workspace`, `ethos-agent`,
and `ethos-project` are migration host packages. They are not the final package
ontology.

Their contents migrate as follows:

- `ethos-governance`: contracts move to `ethos-contracts`; self-evolution and
  release semantics move to `ethos-repository`; provider invocation moves to
  `ethos-adapters`.
- `ethos-workspace`: logical workspace semantics move to `ethos-repository`;
  Git and SQLite implementations move to `ethos-adapters`.
- `ethos-agent`: assistant boundary semantics move to `ethos-assistants`;
  MCP/ACP provider details move to `ethos-adapters`.
- `ethos-project`: adoption and profile semantics move to `ethos-repository`;
  rendering and provider-specific scaffold writers move to `ethos-adapters`.

The npm launcher currently represented by `ethos-node` migrates to
`distributions/npm` and remains launcher-only.
