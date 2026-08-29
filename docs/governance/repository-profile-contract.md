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
machine contracts, docs, rules, evidence, official OpenSpec records,
Attestations, and repo-local projections keep their native authority according
to the governed repository's own order.

## Placement

The stable entrypoint is:

```text
.ethos/profile.toml
```

This path is repository-level. It is not tied to monorepos, Python packages,
`packages/`, `tools/`, or any language runtime. Single-package repositories,
polyglot repositories, documentation repositories, data repositories, and
infrastructure repositories use the same entrypoint.

The `.ethos/` tree is the tracked ETHOS binding layer. Mutable ETHOS state is
repository identity state, not profile-configurable layout: it lives under
`<git-common-dir>/ethos/` so no linked checkout is polluted. Tool-native
configuration remains outside the profile in the repository's configuration
layer.

## Responsibilities

The profile may declare identity, roots for repository-owned capabilities,
explicit normative source files, evidence-root classes, proof gate descriptors,
independent-verification policy, and adoption boundaries.

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

## OpenSpec Applicability

Every mutation-capable adopter declares the repository paths for which official
OpenSpec lifecycle evidence is required. These paths classify applicability;
they do not predict or authorize the files a Change may modify.

`ethos lane prewrite`, `ethos plan --changed`, and `ethos prove` consume the same
official selected Change and fresh Git diff. ETHOS compiles the exact official
projection into a transient Commitment containing only `schema_version`, `id`,
and `acceptance`. It derives changed paths from Git rather than a second scope
carrier.

Work ownership is independent: a Lease contains only `lane_ref`, `holder_ref`,
`generation`, and `expires_at`. Lane creation, archive, continuation, handoff,
and retirement observe the current Lease and Git state, compile one exact ref
intent, recheck source and target immediately before compare-and-swap, and
post-observe the result. No Lease field mirrors HEAD, tree, OpenSpec, Commitment,
paths, workflow progress, or effect outcome.

If official intent changes, ETHOS recompiles the current projection.
Authorization still depends on current ownership, applicable policy, fresh Git
facts, proof, and the exact effect plan; there is no separate binding-repair
lifecycle or manual state-edit path.

## Optional Declarations

The same typed contract can reference existing repository roots, proof gate
descriptors, independent-verification policy, and adoption boundaries. These
sections are interpreted only when declared; adoption does not generate their
carriers. Tool-native configuration and provider state remain outside the profile.

A profile does not declare execution-substrate transition state. Unknown tables
fail closed; ETHOS neither parses nor migrates them into a second lifecycle path.
See [Adopter Boundary And Retirement](adopter-boundary-and-retirement.md) for the
attested transition proof.

Repository-native proof gates use the shared gate descriptor vocabulary. A
profile-native gate id without a descriptor fails closed through
strict profile validation rather than guessing a command.

## Adapter Command Contract

ETHOS profiles reference commands by contract, not by implementation location.
A command contract records command identity, output shape, exit semantics, and
evidence artifact expectations. The command may be implemented by any repository
native tool: Pixi, Make, npm, Cargo, Go, pytest, shell, or a project CLI.

A command contract must not require a universal `packages/`, `tools/`, `scripts/`,
or Python layout. Those are adopter implementation choices.

Repository-native proof gates use the same typed descriptor vocabulary as a
declared gate registry. The `[proof] code_correctness_gates` list names the gates
required for promotion; each profile-native id must also have one `[[proof.gates]]`
descriptor with at least `id`, `kind`, and a list-form executable `command`.
`[proof.code_correctness_map]` explicitly maps the required `behavior` and
`static-analysis` axes to distinct gate IDs. Missing axes, reused gates, undeclared
IDs, and waivers are invalid declarations rather than runtime vocabulary guesses.
Optional descriptor fields such as `depends_on`, `evidence_class`,
`trust_bearing`, and `network_policy` retain the shared gate semantics. ETHOS
compiles these descriptors as the profile's sole native gate owner: they
participate in action graph validation, policy digests, and proof-run
conformance without becoming packaged gates or a second command plane.

An id without a descriptor is not executable truth. The strict profile and gate
declaration contracts reject missing, duplicate, mismatched, cyclic, or incomplete
descriptors before planning; ETHOS never guesses a command or accepts an unverified
proof-run ID.

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
vocabulary: repository, subject, commitment, change, evidence, attestation,
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
capability as not applicable. Lifecycle is not a
`[proof].code_correctness_gates` entry, and no method package is a governance
substitute.
