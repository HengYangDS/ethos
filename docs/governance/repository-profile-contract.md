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
- migration backend selection, when dual backends are still active;
- `external_backend.control`, a repository-local declarative backend control
  manifest such as `.config/interfaces/external-ethos-backend.toml` when an
  adopter records a reversible external backend switch;
- adopter retirement boundaries: the generic binding manifest, the execution
  config root, forbidden product-core adopter roots, external backend state,
  embedded fallback state, and the tracked policy/evidence path proving the
  rollback window.

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

[openspec]
material_paths = [
  ".ethos/profile.toml",
  "openspec/**",
  "docs/governance/**",
  "rules/**",
]
```

## Material OpenSpec Scope

Every adopter profile SHALL declare a non-empty `[openspec].material_paths`
list. These portable repository-relative glob patterns identify edits that
require an active Change companion. Missing or empty declarations fail with
`openspec_material_paths_missing`; malformed declarations fail with
`openspec_material_paths_invalid`. ETHOS does not interpret an empty list as
an opt-out.

For every changed material path, `ethos lane prewrite`, `ethos plan --changed`,
and `ethos prove` use the same official-OpenSpec selected Change list and the
same ETHOS-owned `openspec/changes/<id>/scope.toml` companion read model. A
valid companion covering the path admits it; otherwise the stable diagnostic
is `openspec_material_path_uncovered:<path>`. This companion is adjacent to,
not part of, the official OpenSpec workflow schema. An invalid unrelated
companion remains a Change diagnostic and cannot defeat another selected
Change's valid coverage.

```toml
# openspec/changes/<change-id>/scope.toml
schema_version = 1
paths = [
  ".ethos/profile.toml",
  "openspec/changes/<change-id>/**",
  "docs/governance/**",
]
```

Bootstrap is deliberately narrow. Create the Change with the official
`openspec new change <id>` command, then admit only that exact Change's
otherwise absent `scope.toml`, provided it is a declared material path and the
official list identifies the Change as active. The finished companion must
cover itself and all subsequent material writes. Lifecycle scope remains a
repository-governance obligation, not an entry in
`[proof].code_correctness_gates` and not authority for a method package.

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

An adopter in dual-backend migration may declare a backend control manifest:

```toml
[external_backend]
state = "adoption_preview"
minimum_version = "external>=embedded"
shadow_required = true
control = ".config/interfaces/external-ethos-backend.toml"
```

The control manifest is repository-local declarative configuration, not an
execution wrapper. Its stable shape records `asset_kind =
"ExternalEthosBackendSwitch"`, `profile_binding = ".ethos/profile.toml"`,
`current.state`, `current.default_backend`, `current.external_backend`,
`current.rollback_mode`, allowed transitions, and forbidden shortcuts. The
truth boundary must remain configuration only: the manifest admits or blocks a
backend lifecycle claim; it does not execute ETHOS, replace `.config`, or create
an adopter-local command plane.

An adopter with a pre-existing documentation IA may also declare a docs topology
policy:

```toml
[docs_topology]
state_root_policy = "adopter_declared_compatibility"
time_state_roots = ["docs/current", "docs/future"]
state_metadata_policy = "front_matter_or_status_line"
status_field = "Status"
compatibility_decision = "docs/reference/documentation-information-architecture.md"

[docs_topology.state_value_map]
index = "canonical"
reference = "canonical"
"current governance" = "canonical"
"current implementation" = "canonical"
"operational guidance" = "canonical"
evidence = "canonical"
"delivery evidence" = "canonical"
"dated evidence" = "canonical"
"active plan" = "active"
"target design" = "planned"
"historical context" = "archived"
```

This table is generic adopter policy. It does not make `docs/current/` or
`docs/future/` valid ETHOS product roots, and it does not waive the common
decision/evidence/reference/history kernel. It tells ETHOS that the adopter owns
those existing roots and adopter `Status:` vocabulary through a tracked
documentation-IA decision while it converges or proves retirement readiness.
Missing `compatibility_decision`, unlisted time-state roots, unmapped required status
values, missing kernel paths, invalid mapped state metadata, and role/root
mismatches remain blocking gaps.

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

Repository-native proof gates use the same typed descriptor vocabulary as the
product gate registry. The `[proof] code_correctness_gates` list names the gates
required for promotion; each non-product id must also have one `[[proof.gates]]`
descriptor with at least `id`, `kind`, and a list-form executable `command`.
Optional descriptor fields such as `depends_on`, `evidence_class`,
`trust_bearing`, and `network_policy` retain the product gate semantics. ETHOS
compiles these descriptors as an adopter overlay: they participate in action
graph validation, policy digests, and proof-run conformance without becoming
product-owned gates or a second command plane.

An id without a descriptor is not executable truth. ETHOS reports an
`adopter_gate_descriptor_missing:<id>` gap rather than guessing a command,
accepting an unverified proof-run id, or raising an implementation exception.
Invalid, duplicate, profile-mismatched, or product-conflicting descriptors fail
closed through the corresponding `adopter_gate_descriptor_*` gap.

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

## Retirement Readiness

Embedded-adopter retirement is a profile and evidence verdict, not a product
directory convention. ETHOS checks it through:

```bash
ethos fleet retirement-readiness --target <repo> --json
```

The verdict is generic across monorepos, single repositories, documentation
repositories, data repositories, and infrastructure repositories. It requires:

- `.ethos/profile.toml` as the binding manifest;
- `.config/` as the adopter-owned execution/config root when the adopter uses
  repository-native gate configuration;
- `external_backend.minimum_version = "external>=embedded"`;
- shadow parity evidence with zero false negatives;
- a reversible external-default phase whose profile state matches the
  profile-declared backend control manifest;
- embedded backend freeze as fallback/reference;
- rollback-window evidence before a separate Retirement Decision;
- a `[rollback_window]` profile table, once the external backend becomes the
  reversible default, with `state = "complete"` and completed scenarios for
  `proof_report`, `work_lane_closeout`, `domain_gate`, and
  `assistant_playbook`;
- a rollback-window `evidence_manifest` that is repository-local, tracked by
  Git, parseable as TOML, bound to reachable target and product heads, and
  contains scenario entries with command, evidence path, digest, target-head,
  and product-head bindings for each required scenario;
- absence of adopter-private product roots such as `adopters/<repo>`,
  `profiles/<repo>`, or `tests/fixtures/adopters/<repo>` unless the adopter
  profile explicitly marks them as fixture-only outside product ontology.

A terminal rollback-window profile section is intentionally generic:

```toml
[rollback_window]
state = "complete"
evidence_manifest = "docs/evidence/external-ethos-rollback-window.toml"
completed_scenarios = [
  "proof_report",
  "work_lane_closeout",
  "domain_gate",
  "assistant_playbook",
]
```

Adopters may add more required scenarios, but they may not remove the standard
minimum scenarios. The manifest itself carries the trust-bearing details:

```toml
schema_version = 1
target_head = "<adopter-head-or-ancestor>"
product_head = "<external-ethos-head-or-ancestor>"

[scenarios.proof_report]
target_head = "<same-adopter-head>"
product_head = "<same-external-ethos-head>"
evidence = "docs/evidence/rollback-window/proof-report.json"
command = "ethos prove --execute --expect-head <head> --json"
digest = "sha256:<evidence-digest>"
```

The same scenario shape is required for `work_lane_closeout`, `domain_gate`,
and `assistant_playbook`, plus any adopter-added required scenarios. Missing,
incomplete, untracked, unparsable, path-escaping, or head-unbound rollback
evidence keeps the retirement-readiness verdict open even if the external
backend state claims `retirement_ready`.

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


## OpenSpec Lifecycle

A valid adopter uses the same official OpenSpec lifecycle in planning and proof
as the product. Lifecycle is not a `[proof] code_correctness_gates` entry.
Portable material-path scope admission is deferred to the explicit OpenSpec
Change `adopter-material-change-scope-20260714`; no method package is a
governance substitute.
