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
machine contracts, docs, rules, evidence, OpenSpec records, Commitments,
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

## Material OpenSpec Scope

Every adopter profile SHALL declare a non-empty `[openspec].material_paths`
list. These portable repository-relative glob patterns identify edits that
require an active Commitment. Missing or empty declarations fail with
`openspec_material_paths_missing`; malformed declarations fail with
`openspec_material_paths_invalid`. ETHOS does not interpret an empty list as
an opt-out.

For every changed material path, `ethos lane prewrite`, `ethos plan --changed`,
and `ethos prove` use the same official-OpenSpec selected Change list and the
same `openspec/changes/<id>/commitment.toml` scope. A valid contract covering the path admits it; otherwise the stable diagnostic
is `openspec_material_path_uncovered:<path>`.

```toml
# openspec/changes/<change-id>/commitment.toml
schema_version = 1
id = "change:<change-id>"
intent = "Describe the intended outcome."
subjects = ["repository:self"]
scope = [
  ".ethos/profile.toml",
  "openspec/changes/<change-id>/**",
  "docs/governance/**",
]
```

Create the first Change through the normal Work Lane start path. After a Change
has been archived, an existing owned lane starts its next atomic generation with
the public exact transition:

```bash
ethos lane start-change <change-id> \
  --intent "<bounded intent>" \
  --scope "<repository-relative glob>" \
  --expect-head "$(git rev-parse HEAD)" \
  --apply --json
```

If the forward fix already exists in the lane, stage exactly that bounded
overlay, run the command once without `--apply`, and pass the returned
`overlay.digest` back as `--expected-overlay-digest` when applying. ETHOS then
commits the overlay and the new Commitment together; unstaged, uncovered, or
changed bytes are rejected without consuming the transition.

The transition requires the current holder, a valid Lease bound to the archived
Commitment, an exact clean HEAD/tree, and no active Change. It uses the locked
official OpenSpec creator, commits the new Change and Commitment through normal
hooks, then advances the Lease HEAD/tree/carrier/epoch and emits typed effect
evidence. A retry recognizes the completed effect or resumes the exact
post-commit/pre-rebind state; different holders, stale observations, drift, and
unrelated replay remain fail closed. No bootstrap exception, unarchive path,
manual state edit, or second scope-write path exists.

An existing owned lane replaces an immutable Commitment through
`ethos lane rebind-commitment`. Rebind authority belongs to that public
operation's exact same-holder Lease transition, not to a permission that the old
Commitment must anticipate. The operation can therefore introduce a newly
required permission without a bootstrap cycle, while remaining bound to one
branch ref, old/new Commitment digests, carrier bytes, Lease generation,
HEAD/tree/index, overlay, and target commit. The authority is not inherited by
ordinary Git effects and any coordinate drift fails closed.

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
