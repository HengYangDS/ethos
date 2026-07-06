---
subject: ethos:repository-profile-contract
role: policy
state: canonical
relations:
  canonical_for: adopter profile entrypoint, repository profile validation, and external ETHOS adoption boundaries
---

# Repository Profile Contract

ETHOS governs a repository through a repository-level profile. The profile is a
binding manifest: it tells ETHOS which repository surfaces to read, which local
state roots are host-local, which profile contract version is in force, and which
backend is active during adoption or retirement.

The profile does not own repository truth. Source, tests, package metadata,
machine contracts, docs, rules, evidence, OpenSpec records, claims, and
repo-local projections keep their native authority according to the governed
repository's own order.

## Placement

The stable entrypoint is:

```text
.ethos/profile.toml
```

This path is repository-level. It is not tied to monorepos, Python packages,
`packages/`, `tools/`, or any language runtime. Single-package repositories,
polyglot repositories, documentation repositories, data repositories, and
infrastructure repositories use the same entrypoint.

The `.ethos/` tree is the ETHOS binding layer. It may also contain ignored local
ETHOS state under `.ethos/state/`. Tool-native configuration remains outside the
profile in the repository's configuration layer.

## Responsibilities

The profile may declare:

- profile identity and contract version;
- repository kind and root subject;
- roots for rules, docs, durable evidence, OpenSpec, claims, and repo-local
  skills;
- references to tool configuration and boundary configuration;
- durable, generated, and host-local evidence roots;
- migration backend selection, when dual backends are still active.

The profile must not declare:

- tool-native configuration bodies;
- adapter implementation code location as a required layout;
- domain truth copied from adopter rules or docs;
- evidence artifacts;
- host-local state as durable evidence;
- alternate semantics for `ethos status`, `ethos plan`, `ethos prove`,
  `ethos land`, or `ethos publish`.

## Minimal Shape

A conforming profile has this shape:

```toml
schema_version = 1
profile_id = "example"
profile_version = "1"
ethos_contract_version = "1"

[repository]
kind = "software"
root_subject = "git-repository"

[roots]
tool_config = ".config"
rules = "rules"
docs = "docs"
durable_evidence = "docs/evidence"
openspec = "openspec"
claims = "claims"
agent_skills = ".agents/skills"
local_state = ".ethos/state"

[evidence]
generated_roots = ["build/evidence"]
host_local_roots = [".ethos/state", ".cache/local-state"]
```

An adopter may add references to existing repository configuration:

```toml
[config]
checks_catalog = ".config/checks/catalog.toml"
import_boundaries = ".config/boundaries/imports.ini"
module_boundaries = ".config/boundaries/modules.toml"
external_interfaces = ".config/interfaces/external.toml"
worktree_closeout = ".config/worktree/closeout.toml"
worktree_hydration = ".config/worktree/hydration.toml"
```

During migration from an older ETHOS projection, previous projection files may
be listed as transition inputs:

```toml
[previous_projection]
project = ".ethos/project.toml"
workspace = ".ethos/workspace.toml"
rules = ".ethos/rules.toml"
assistants = ".ethos/assistants.toml"
```

Previous-projection entries are not the terminal contract. They are transition
aids until the profile-derived governance context is proven equivalent or
stricter.

## Adapter Command Contract

ETHOS profiles reference commands by contract, not by implementation location.
A command contract records command identity, output shape, exit semantics, and
evidence artifact expectations. The command may be implemented by any repository
native tool: Pixi, Make, npm, Cargo, Go, pytest, shell, or a project CLI.

A command contract must not require a universal `packages/`, `tools/`, `scripts/`,
or Python layout. Those are adopter implementation choices.

## Validation

A repository profile validator must fail closed when:

- `.ethos/profile.toml` is missing;
- the schema is invalid;
- a referenced file is missing;
- a host-local state root is tracked as durable truth;
- durable evidence is placed under a local state root;
- a profile requires `packages/`, `tools/`, `system/`, a monorepo workspace, or a
  Python package layout;
- a profile redefines public command semantics;
- an adapter command lacks declared output shape or exit semantics;
- changed paths cannot be classified and no explicit unknown-path policy exists.

## Product Boundary

ETHOS product code, schemas, and kernel contracts stay in generic repository
vocabulary: repository, subject, commitment, change, evidence, claim, chronicle,
profile, gate, adapter, provider, projection, and backend. A reference adopter
may provide evidence and fixtures, but adopter-private terms must not become
product ontology.

Status: see front matter.

Purpose: define the stable adopter profile entrypoint and validation contract.

See also: [Product Design Contract](product-design-contract.md),
[Config Boundary Model](config-boundary-model.md), and
[Adopter Boundary And Retirement](adopter-boundary-and-retirement.md).
