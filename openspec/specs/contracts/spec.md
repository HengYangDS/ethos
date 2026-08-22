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

### Requirement: TransitionPlan Transition Contract

`TransitionPlan` SHALL remain immutable, deterministic, operation-bound derived
IR. Commitment SHALL NOT carry reusable permissions. Stored plan bytes MAY
support exact recovery but SHALL NOT become a semantic root.

#### Scenario: A transition plan is inspected

- **WHEN** ETHOS compiles a governed change
- **THEN** it exposes ordered checks, decisions, effects, exact operation
  authority, and a closed verdict
- **AND** every dependency is acyclic and effect authority is plan-bound

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
- **THEN** it requires non-compensating role ceilings and a jointly derived
  global ceiling, one bounded `scc` command with
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

### Requirement: Commitment v2 identity is explicit and bounded

Commitment v2 SHALL require every identity-bearing field explicitly and compute
a domain-separated digest over its canonical projection. It SHALL include typed
predecessors, selected Attestations, dependencies, hypotheses, falsifiers, and
experiment protocols, and SHALL exclude reusable permissions and mutable state.
Strings and keys SHALL be Unicode scalar values preserved without normalization;
identifiers SHALL use lowercase ASCII colon-separated segments; timestamps SHALL
use the strict canonical RFC 3339 UTC form; canonical JSON SHALL use RFC 8785
string escaping and UTF-16 key ordering with UTF-8 output, unique object keys,
no insignificant whitespace, and only null, booleans, strings, I-JSON safe
integers, arrays, and objects. Floats, duplicate object keys, lone surrogates,
noncanonical member bytes, and implicit Unicode normalization SHALL be invalid.

String sets SHALL sort by canonical JSON bytes; digest sets SHALL sort
lexicographically. Carrier sets already SHALL be in that order rather than
silently normalized. Dependencies SHALL be `{kind,target,attributes}`;
hypotheses SHALL be `{id,kind,body}`; falsifiers SHALL be
`{id,hypothesis_id,kind,body}`; experiment protocols SHALL be
`{id,hypothesis_ids,kind,body}`. Every nested field SHALL be required, open
`body` and `attributes` values SHALL use the same canonical JSON grammar, and
their declared tuple keys SHALL determine deterministic ordering and duplicate
rejection.

Predecessors SHALL be a canonical set of Commitment digests defining immutable
backward lineage edges. A predecessor set MAY be empty, MAY fork one predecessor
into several successor Commitments, and MAY join several predecessors into one
successor Commitment. Historical Commitments SHALL NOT be mutated with successor
links. Lineage SHALL remain distinct from execution `dependencies`.

#### Scenario: A v2 Commitment is loaded

- **WHEN** carrier bytes omit an identity field, contain a duplicate, use a
  context-dependent subject alias, or fail a typed value contract
- **THEN** validation blocks before a semantic digest is produced

#### Scenario: Equivalent runtime values are projected

- **WHEN** source, wheel, and package-only runtimes load the same valid v2 bytes
- **THEN** they produce byte-identical canonical JSON and the same
  `ethos.commitment.v2` domain-separated digest
- **AND** a float, lone surrogate, duplicate key, non-canonical time,
  out-of-range integer, or unsorted set is rejected rather than normalized
  silently

#### Scenario: Selected intent becomes normative

- **WHEN** input is accepted for implementation
- **THEN** a successor Commitment binds predecessor and selection identities
- **AND** the predecessor Change is not silently expanded

#### Scenario: Governed Changes fork and join

- **GIVEN** immutable predecessor Commitments exist in the selected exact Git
  tree
- **WHEN** separate successors select one predecessor or one successor selects
  several predecessors
- **THEN** each successor binds its complete canonical predecessor set in its
  own digest
- **AND** no historical Commitment or successor index is mutated
- **AND** execution dependencies remain a separate typed field

### Requirement: Attestation v2 payload and relations are open and composable

Attestation v2 SHALL bind an open predicate, `{kind, body}` payload, canonical
relations, evidence, validity, closed verdict, exact digests, and
`mints_authority=false`. Relations SHALL sort by kind, target kind, target id,
and canonical attributes and SHALL reject duplicate values and duplicate
relation identity keys. Every field SHALL be explicit; nullable digest and
validity bindings SHALL project as `null`; advisories and evidence refs SHALL be
sorted unique strings. Payload bodies and relation attributes SHALL obey the
same closed canonical JSON value grammar as Commitment v2. At least one evidence
reference, exact digest binding, or relation SHALL be present.

#### Scenario: Identical text occurs twice

- **WHEN** it appears at distinct source occurrence coordinates
- **THEN** two Attestations retain distinct identities
- **AND** text digest alone is not occurrence identity

#### Scenario: Known and future relations coexist

- **WHEN** an Attestation carries several known relations and an unknown one
- **THEN** all canonical values round-trip in deterministic order
- **AND** only evaluator-understood relations participate in a verdict

### Requirement: Selection Attestations never mint authority

A selection Attestation SHALL dispose input to a named semantic owner, explicit
absence reason, contradiction, or model gap. It SHALL NOT mutate an active
Commitment, Change, scope, acceptance set, or task graph.

#### Scenario: Feedback arrives outside the active Commitment

- **WHEN** it is relevant but not already required by the bounded Change
- **THEN** its selection remains available to a successor Commitment
- **AND** current effect scope remains unchanged
