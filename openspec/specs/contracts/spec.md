# ETHOS Contracts

## Purpose

ETHOS SHALL define provider-neutral schemas, result envelopes, adapter
interfaces, policy records, evidence contracts, and operation or gate contracts
before provider implementations.
## Requirements
### Requirement: Provider-neutral Contracts
ETHOS SHALL keep JSON schemas, TOML config contracts, public result contracts,
attestation envelopes, and evidence contracts free of provider-specific
execution behavior.

#### Scenario: Contracts are inspected
- **WHEN** architecture tests scan `contracts`
- **THEN** contract modules do not import Git, SQLite, subprocess, hosted CI,
  assistant runtime, or adopter-private implementation modules

### Requirement: Trust Envelope Contract
ETHOS SHALL define a provider-neutral trust envelope contract for claim
admission and proof consumers.

#### Scenario: Trust envelope is emitted
- **WHEN** ETHOS reports active claim governance
- **THEN** every trust envelope includes claim id, claim state, boundary,
  evidence, carriers, fallback, kill signal, promotion, and required gaps

### Requirement: Promotion Target Contract
ETHOS SHALL define promotion targets as provider-neutral repository authority
references.

#### Scenario: Promotion target is validated
- **WHEN** ETHOS validates a promotion target
- **THEN** the target kind is one of source, tests, docs, schema, openspec, or
  evidence
- **AND** the target path is repository-relative

### Requirement: Capability Profile Contract
ETHOS SHALL define capability profiles that map OpenSpec capabilities to owner,
boundary, routing, and proof metadata.

#### Scenario: Capability profile is inspected
- **WHEN** ETHOS validates capability profile metadata
- **THEN** the profile names a family, owner object, primary invariant,
  routing question, boundary rules, and proof profile

### Requirement: Governed Repository Context Contract
ETHOS SHALL define a governed repository context contract for every repository
subject. This is the shared governance context contract for repository audit,
proof and command payloads.

#### Scenario: Governance context is provider-neutral
- **WHEN** ETHOS emits `governance_context`
- **THEN** the context identifies the subject as a repository
- **AND** the context records the profile, kernel
  chain, and singular lifecycle command semantics
- **AND** `shared_commands` and `transition_commands` contain the five transition
  commands
- **AND** `reader_projection_commands` contains `ethos status`
- **AND** provider, host, editor, model, and toolchain choices remain outside
  product semantics

### Requirement: Provider-neutral Skill Activation Contract

ETHOS SHALL represent skill activation through a provider-neutral contract IR
that preserves historical activation fixture rows while exposing V2 ownership,
operation, lifecycle, routing, composition, package, projection, and proof
metadata.

#### Scenario: historical activation normalizes without data loss

- **GIVEN** a v1 `.agents/skills/activation.toml` record with `id` or `name`
- **WHEN** ETHOS loads skill activation contracts
- **THEN** the normalized IR preserves the declared identifier source,
  subjects, path, path globs, intent tokens, pre-reads, post-checks,
  co-activation hints, commands, boundary fields, and fixture-specific
  extension fields
- **AND** the output remains readable for existing playbook JSON records

#### Scenario: strict activation requires V2 ownership

- **GIVEN** a playbook check runs in `v2-strict` mode
- **WHEN** an active primary skill lacks subject, operation, lifecycle, path
  coverage, package manifest, command affordances, or proof obligations
- **THEN** ETHOS reports deterministic required gaps

### Requirement: Skill Package Manifest

ETHOS SHALL bind provider-visible skill packages to content-addressed package
manifests that declare entrypoint, included files, required sections, digest
algorithm, quality rules, and capability classes.

#### Scenario: package digest mismatch is detected

- **GIVEN** a skill package manifest declares included files and an expected
  digest
- **WHEN** the package contents no longer match that digest
- **THEN** `ethos playbooks check --mode v2-strict --json` reports a required
  package digest gap

#### Scenario: unsafe package paths are rejected

- **GIVEN** a package manifest path, entrypoint, or included file uses an
  absolute path or a path escaping its allowed root
- **WHEN** ETHOS validates the manifest
- **THEN** validation reports a required package path gap without reading
  outside the repository or package directory

#### Scenario: package capabilities are classified

- **GIVEN** a package manifest declares command, MCP, script, or host
  capabilities
- **WHEN** ETHOS validates the manifest
- **THEN** readonly capabilities reject mutating commands, proof capabilities
  identify proof commands, and guarded mutation capabilities declare a guard

### Requirement: Explicit mutation context contract
ETHOS SHALL define mutation-capable operations with explicit target-root,
checkout-role, editor-root, target-path, and admission-result fields.

#### Scenario: Mutation context is auditable
- **WHEN** a mutation-capable operation is admitted or blocked
- **THEN** the machine result includes target root, editor root, branch role,
  target paths, decision, and required gaps

### Requirement: Documentation carrier contract
ETHOS SHALL distinguish human-facing Markdown, durable TOML config, public JSON
command output, ecosystem-native YAML, generated JSONL, ignored local indexes,
and tracked evidence by author, lifecycle, and truth status.

#### Scenario: Machine and human carriers do not collapse
- **WHEN** ETHOS defines a repository governance record
- **THEN** durable hand-authored configuration uses TOML unless an ecosystem
  standard requires another carrier
- **AND** public command and MCP payloads use JSON
- **AND** human judgment, design, reviews, and retrospectives use Markdown

### Requirement: Projection digest contract
ETHOS SHALL require generated tracked agent or host projections to carry source
identity sufficient for drift detection.

#### Scenario: Projection drift is checkable
- **WHEN** ETHOS generates a tracked agent or host projection
- **THEN** the projection records its source surface or digest
- **AND** a later drift check can determine whether the projection is stale

### Requirement: Capability Profile Facet Contract

ETHOS SHALL define capability profiles with decision axes and recommended facets
so OpenSpec proposal routing can be validated without hardcoded domain terms.

#### Scenario: Capability profile declares routing facets

- **WHEN** ETHOS validates a product capability profile
- **THEN** the profile includes decision axes used for routing and review
- **AND** recommended facets describe local valid values for proposal metadata
- **AND** aliases remain optional diagnostic metadata rather than routing truth.

### Requirement: PlanIR Transition Contract
ETHOS SHALL compile provider-neutral ChangeContract and RepositoryFacts inputs
through one strict lifecycle declaration into deterministic PlanIR. A parallel
run-state read model, event stream, or external orchestration store MUST NOT own
lifecycle truth.

#### Scenario: A transition plan is inspected
- **WHEN** ETHOS compiles a governed change
- **THEN** PlanIR exposes ordered checks, decisions, effects, permissions, and a closed verdict
- **AND** every dependency is acyclic and every effect is permission-bounded

### Requirement: Handoff Package Contract
ETHOS SHALL define digest-bound handoff packages as context projections over
repository truth.

#### Scenario: Handoff package is validated
- **WHEN** a handoff package is inspected
- **THEN** it records source refs, source digests, target actor, intended use, freshness state, and proof/evidence refs
- **AND** stale source digests block trust-bearing handoff claims
- **AND** handoff content remains context until promoted into evidence or chronicle

### Requirement: Declarative Registry Compilation

ETHOS SHALL compile durable coupling and standards registry facts from strict
frozen TOML contracts before emitting public projections.

#### Scenario: A valid declaration projects stable registry data

- **WHEN** a registry declaration is loaded
- **THEN** its contract validates before projection
- **AND** declared static fields preserve order and payload shape
- **AND** runtime facts are added only at adapter boundaries

#### Scenario: An invalid declaration is rejected before projection

- **WHEN** a declaration contains unknown fields, duplicate ids, or malformed admission data
- **THEN** no partial public registry is emitted
- **AND** declaration-level tests cover the rejection

### Requirement: Direct Source Measurement Contract

ETHOS SHALL expose one direct, fail-closed repository source measurement report
without a carrier-model hierarchy, metric registry, worker protocol, snapshot or
replay runtime, shadow model, or debt contract.

#### Scenario: The measurement policy is loaded

- **WHEN** ETHOS loads `.config/checks/format/selection.toml`
- **THEN** it requires terminal ceilings no greater than 54,000 for
  `python_total` and 68,000 for `global_total`, one bounded `scc` command with
  exact non-negative tolerances, a fixed canonicalization line width, named
  aggregate members, and admitted format budget rows
- **AND** `global_total` contains every admitted category exactly once and
  `python_total` contains every Python category exactly once
- **AND** invalid shape, duplicate or unknown aggregate membership, incomplete
  category coverage, or relaxation relative to the accepted policy returns no
  partial clean policy
- **AND** the first versioned policy enters accepted truth only through the
  existing candidate-external control-replacement verifier; it does not create a
  second budget declaration.

#### Scenario: Git inventory is measured deterministically

- **WHEN** ETHOS measures a repository
- **THEN** it obtains one sorted inventory of tracked and non-ignored untracked
  Git-present regular files contained by the repository and preserves executable
  mode as an inventory fact
- **AND** each admitted path is classified once by declared extension and
  optional path patterns, or by a declared shebang when an executable has no
  extension
- **AND** a Git-present executable that has neither an admitted extension nor an
  admitted shebang produces a required unclassified-executable gap
- **AND** the inventory digest is derived from sorted path, category, and effective
  line observations rather than checkout location or iteration order.

#### Scenario: Python ELOC has one semantic owner

- **WHEN** Python source is measured from text or a file
- **THEN** `effective_code_lines_for_source` owns blank, comment, docstring, bare
  string-expression, inline-comment, and syntax-error fallback semantics
- **AND** file measurement reads source and delegates without a parallel parser.

#### Scenario: Canonicalization cannot be gamed

- **WHEN** an admitted non-Python carrier is reformatted, minified, line-joined,
  key-reordered, generated in another admitted carrier, or moved between owned
  categories without deleting its executable semantics
- **THEN** its declared format-specific parser and canonical serializer or
  meaningful-text canonicalization retains the semantic footprint
- **AND** measurement uses the greater of meaningful physical lines and the
  fixed-width canonical representation where that format requires it
- **AND** category movement changes inventory classification but cannot create
  false global deletion credit or cross-category compensation.

#### Scenario: The independent counter disagrees

- **WHEN** `scc` is unavailable, emits invalid output, omits an admitted
  canonical file, or reports either `python_total` or `global_total` above or
  below canonical measurement beyond the declared tolerance
- **THEN** the report blocks with the observed disagreement
- **AND** it records both independent observations and does not select either
  favorable number or synthesize a passing total.

### Requirement: Container contracts are opt-in, provider-neutral, and product-schema-bound

ETHOS SHALL validate a container-delivery contract only when an adopter profile
declares `[container_contract]`. The declaration and referenced manifest SHALL
be validated with product-owned schemas and SHALL not become valid through an
adopter-local relaxed schema copy.

#### Scenario: Undeclared repository remains valid

- **WHEN** a governed repository has no container-contract declaration
- **THEN** validation reports `not_declared` without a required gap
- **AND** it does not infer that container delivery is required.

#### Scenario: Declared contract binds a contained manifest

- **WHEN** an adopter profile declares a contract manifest below its repository
  root
- **THEN** ETHOS validates the declaration and manifest with product schemas
- **AND** a missing, directory, unreadable, or root-escaping manifest produces
  a required gap.

#### Scenario: Semantic delivery evidence is fail-closed

- **WHEN** a declared manifest omits required Linux architecture smoke evidence,
  uses untracked or hash-mismatched evidence, duplicates an asset identifier,
  omits persistent restore policy, names a prohibited runtime vendor, or
  references an invalid untrusted output schema
- **THEN** validation produces a stable required gap
- **AND** schema reporting includes that gap in normal promotion readiness.

#### Scenario: Valid evidence remains provider-neutral

- **WHEN** a declared manifest contains exactly the required architecture and
  recovery evidence with matching tracked digests
- **THEN** validation is valid
- **AND** it makes no hosted-CI, image-publication, or local-runtime success
  claim.
