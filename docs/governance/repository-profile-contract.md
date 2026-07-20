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
state roots are host-local, and which optional policies are explicitly active.

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

The profile may declare identity, roots for repository-owned capabilities,
explicit normative source files, evidence-root classes, proof gate descriptors,
independent-verification policy, docs topology, a container contract, adoption
boundaries, and explicit backend-retirement state.

The profile must not declare:

- tool-native configuration bodies;
- adapter implementation code location as a required layout;
- domain truth copied from adopter rules or docs;
- evidence artifacts;
- host-local state as durable evidence;
- alternate semantics for `ethos status`, `ethos plan`, `ethos prove`,
  `ethos land`, or `ethos publish`.

## Minimal Shape

The bootstrap renderer writes the smallest valid declaration:

```toml
profile_id = "example"

[openspec]
material_paths = [
  ".ethos/profile.toml",
  "openspec/**",
  "docs/governance/**",
  "rules/**",
]
```

`profile_id` and every material-path item are non-empty. Pydantic v2 rejects
unknown fields and invalid types; the loaded declaration is frozen. Omitted
sections use contract-owned defaults rather than repeated generated text.

### Former Profile Envelope

ETHOS accepts one explicit former envelope while adopters migrate: the complete
`schema_version = 1`, `profile_version = "1"`,
`ethos_contract_version = "1"`, and two-field `[repository]` metadata block.
Those retired fields are removed before the current strict declaration is
validated. Partial, malformed, or extended legacy data is not compatibility
input and remains `adopter_profile_invalid:.ethos/profile.toml`.

### Normative Sources

`roots.rules` remains a safe repository-relative root; it is not the repository
root and it must not be used to pretend that a single file is a directory. An
adopter whose normative authority is a root-level file declares that fact
separately:

```toml
normative_sources = ["guidelines.md"]
```

ETHOS includes these files in evidence-root candidates but does not copy,
relocate, or otherwise redefine their native authority.

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
is `openspec_material_path_uncovered:<path>`.

```toml
# openspec/changes/<change-id>/scope.toml
schema_version = 1
paths = [
  ".ethos/profile.toml",
  "openspec/changes/<change-id>/**",
  "docs/governance/**",
]
```

Create a Change through the official OpenSpec command before later material
writes. Adoption itself writes the complete material-path declaration, so no
historical profile bootstrap exception or second profile-write path remains.

## Optional Declarations

The same typed contract can reference existing repository roots, proof gate
descriptors, independent-verification policy, container contracts, and explicit
backend-retirement state. These sections are interpreted
only when declared; adoption does not generate their carriers. Tool-native
configuration and provider state remain outside the profile.

An adopter that declares backend retirement may set `external_backend.control`
to a repository-local manifest whose asset kind is
`ExternalEthosBackendSwitch`. That manifest records `default_backend`,
`external_backend`, and `rollback_mode`. Its truth boundary is configuration only:
it admits or blocks a lifecycle claim but never executes ETHOS or creates
a command wrapper.

Repository-native proof gates use the product gate descriptor vocabulary. A
non-product gate id without a descriptor fails closed through
`adopter_gate_descriptor_missing:<id>` rather than guessing a command.

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

## Optional Container Contract

An adopter that needs a portable container-delivery assurance boundary may opt
in through its profile rather than through a new command plane:

```toml
[container_contract]
schema_version = 1
manifest = ".ethos/container-contract.toml"
```

The manifest is validated against ETHOS-owned schemas. It declares evidence for
the required Linux architectures, delivery artefacts, trusted and untrusted
execution boundaries, lifecycle recovery, and the complete asset inventory.
Every referenced evidence file must remain below the adopter root, be tracked,
and match its declared SHA-256. The contract is provider-neutral: it does not
select or certify a workstation runtime, a hosted provider, or an image
publication.

An absent declaration is advisory and does not impose container requirements.
A declared malformed manifest, relaxed local schema copy, path escape, stale
evidence digest, incomplete recovery policy, or invalid untrusted output schema
is a normal schema-report required gap.

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

A valid adopter uses the official OpenSpec lifecycle when a workspace exists,
OpenSpec is explicitly requested, or a changed path matches declared
`material_paths`. Without those applicability facts, plan and proof report the
capability as not applicable. Lifecycle is not a `[proof]
code_correctness_gates` entry, and no method package is a governance substitute.
