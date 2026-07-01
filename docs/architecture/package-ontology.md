---
subject: ethos:target-package-ontology
role: decision
state: canonical
relations:
  canonical_for: target product package topology
---

# Package Ontology

The repository contains the buildable product package homes.

No active product migration host remains in `packages/`.

The Python product package ontology is:

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

Git-native repository operation lifecycle semantics. Owns status, plan, prove,
land, publish, intake, campaign, quality and determinism semantics, command
surface semantics, evidence freshness semantics, local state logical model,
workspace/lane logical model, and branch-role/worktree semantics.

It answers one question: how one human-agent repository change is planned,
proved, landed, published, remembered, and evolved.

It must not shell out to providers directly. Provider work is delegated through
`ethos-adapters`.

### `ethos-assistants`

Assistant-facing repository operation boundary. Owns Playbooks, assistant
surfaces, method packs, context providers, projection classification, truth
boundaries, changed-scope routing to playbooks, and assistant doctor models.

It is named `ethos-assistants` rather than `ethos-agent` because ETHOS governs
assistant/context boundaries; it does not implement an agent.

### `ethos-adapters`

Provider-specific integrations. Owns adapters for Git command execution, SQLite,
official OpenSpec, Backlog, GitHub, GitLab, MCP, ACP, Superpowers detection,
Dagger, Pants, Bazel, Nx, SLSA, in-toto, Sigstore, pre-commit, Ruff, pytest,
nox, pixi, and hosted CI.

Adapters observe, execute, translate, and bind evidence. They do not own
product semantics. Git semantics remain native to ETHOS; this package only owns
execution and projection boundaries around those semantics.

### `ethos`

Public CLI surface. Owns cyclopts command tree, UX composition, human-readable
rendering, and JSON output routing.

The CLI must remain a thin shell and must not become the semantic center.
The CLI depends only on target product packages.

### `ethos-test`

Conformance, parity, and proof host. Owns conformance fixtures, sample
repositories, golden JSON outputs, adapter contract tests, schema compatibility
tests, migration replay fixtures, and shadow parity harnesses.

## Migration State

The external ETHOS product repository has retired the internal product
migration-host packages. The current state is:

- Python product packages: complete in `packages/ethos-*` and `packages/ethos`.
- npm launcher: migrated to `distributions/npm`.
- product package migration hosts: none.

This does not delete or decide the lifecycle of embedded ETHOS implementations
inside adopter repositories such as alphasim-dmgr. Those adopters still follow
the separate capability parity, external shadow parity, freeze, rollback window,
and retirement decision process.

Historical product family dispositions are retained only as retired-family
explanations. `ethos-workspace` moved Git-native lifecycle semantics to
`ethos-repository` and local command execution to `ethos-adapters`; it is not a
generic VCS abstraction and is no longer an active product migration host.
