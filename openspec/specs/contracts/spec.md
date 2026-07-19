# ETHOS Contracts

## Purpose

ETHOS SHALL define provider-neutral schemas, result envelopes, adapter
interfaces, policy records, evidence contracts, and command registry contracts
before provider implementations.
## Requirements
### Requirement: Provider-neutral Contracts
ETHOS SHALL keep JSON schemas, TOML config contracts, public result contracts,
attestation envelopes, evidence contracts, and package ontology records free of
provider-specific execution behavior.

#### Scenario: Contracts are inspected
- **WHEN** architecture tests scan `contracts`
- **THEN** contract modules do not import Git, SQLite, subprocess, hosted CI,
  assistant runtime, or adopter-private implementation modules

### Requirement: Package Ontology Contract
ETHOS SHALL expose the target product package ontology as a machine-readable
contract.

#### Scenario: Package ontology is reported
- **WHEN** `ethos quality package-ontology --json` runs
- **THEN** ETHOS reports target product packages, distribution adapters,
  migration host state, and physical target home readiness from one canonical
  contract

### Requirement: Migration Host Retirement Contract
ETHOS SHALL report active product migration hosts as an empty set when product
topology migration is closed.

#### Scenario: Package ontology is audited after migration closure
- **WHEN** `ethos quality package-ontology --json` runs
- **THEN** `migration_hosts` is empty
- **AND** `migration_status` is `complete`
- **AND** distribution adapters are reported separately from Python packages

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
proof, and report payloads.

#### Scenario: Governance context is provider-neutral
- **WHEN** ETHOS emits `governance_context`
- **THEN** the context identifies the subject as a repository
- **AND** the context records the profile, kernel
  chain, and transition, reader-view, and scorecard command semantics
- **AND** `shared_commands` and `transition_commands` contain the five transition
  commands
- **AND** `reader_view_commands` contains `ethos orient`
- **AND** `scorecard_commands` contains `ethos report`
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

### Requirement: Workflow Runtime Contract
ETHOS SHALL define workflow runtime contracts as provider-neutral schemas and
TOML declarations over derived repository facts. Event entities are admitted
only when a tracked production path creates them and a tracked consumer,
reducer, or evidence boundary uses them.

#### Scenario: Workflow contract is inspected
- **WHEN** ETHOS validates `system/workflows.toml`
- **THEN** the contract exposes lifecycle states, transitions, guard names, required facts, node kinds, enforcement modes, run-state locality, handoff locality, and eval metrics
- **AND** it does not expose a declaration-only event stream, event count, or event-locality field
- **AND** every transition references declared states and guards
- **AND** every blocking invalid-state reference maps to the ETHOS invalid-state taxonomy
- **AND** no workflow contract requires `.comet`, `.taskmaster`, `.specify`, or another external runtime store as authority

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

### Requirement: Metric-Domain Budget Contract

ETHOS SHALL define repository budgets as versioned measures inside explicit
carrier and scope domains rather than as one convertible cross-language scalar.

#### Scenario: Repository source is measured by native domains

- **WHEN** ETHOS defines Budget Contract v2 metrics
- **THEN** programming source SHALL use language-native lexical tokens and
  normalized syntax or payload bytes
- **AND** structured declarations SHALL use semantic nodes and normalized scalar
  payload bytes
- **AND** templates SHALL separate dynamic structure from static payload
- **AND** tests, evidence, derived projections, documentation, and authored
  product source SHALL remain distinct scopes
- **AND** hard coordinates SHALL combine with logical AND without weighted or
  cross-coordinate compensation.

#### Scenario: Metric semantics are content-addressed

- **WHEN** a carrier is measured
- **THEN** the observation SHALL bind the metric version, parser or lexer,
  parser version, grammar digest, normalization version, aggregation rule,
  carrier rule, repository-relative path, and content identity
- **AND** parser unavailability, invalid input, ambiguous classification, or an
  unsupported governed carrier SHALL produce a required gap rather than zero.

#### Scenario: Agent tokens remain operational

- **WHEN** ETHOS budgets an agent prompt, model context, or generated response
- **THEN** model/tokenizer-specific BPE tokens MAY govern that operational scope
- **AND** those tokens SHALL NOT become repository-source truth or a conversion
  basis for source-budget coordinates.

### Requirement: Typed Source Budget Carrier Manifest

The repository SHALL own a versioned Budget Contract v2 carrier manifest whose
strict immutable models classify every maintained Git-present path as exactly
one measured carrier identity or one explicit reviewed exclusion. The loader
SHALL reject unknown fields, duplicate identities or matcher identities, empty
or invalid repository-relative POSIX matchers, the declared non-canonical
matcher syntax and redundancy set, and invalid measure/exclusion combinations.
Classification SHALL evaluate every rule without priority or first-match
semantics and SHALL report zero matches, multiple matches, or unsupported
governed extensions as required gaps.

The repository adapter SHALL enumerate present tracked and non-ignored untracked
paths through one tagged Git observation. A successful inventory SHALL contain
non-empty, unique, stably ordered regular paths. Git command failure, `OSError`,
malformed output, an empty inventory, unsupported tracked modes, symlinks,
gitlinks, symlinked ancestors, unreadable objects, or object-mode mismatch SHALL
produce required gaps and SHALL NOT expose a clean partial inventory. The
manifest and inventory digests SHALL be deterministic under declaration order,
path enumeration order, locale, timezone, and absolute checkout location.
`CarrierMatch` SHALL carry an explicit `path_state`, reject non-canonical
valid paths, reject malformed safe labels for invalid paths, and reject empty or
unstable matched IDs and gap tokens. Synthetic status SHALL NOT be inferred from
pathname text. `CarrierInventory` SHALL preserve distinct valid and invalid
matches that share the same display label, require unique stable
`(relative_path, path_state)` keys, and reject incorrect gap aggregation,
identity-field tampering, or a digest that does not match canonical content.

#### Scenario: A path has exactly one measured carrier

- **WHEN** a valid repository-relative path matches one measured carrier rule
  and no exclusion
- **THEN** classification SHALL return that immutable carrier identity, its
  metric profile, a `classified` state, and no classification required gap

#### Scenario: A path is explicitly excluded

- **WHEN** a path matches one exclusion with a non-empty owner and reviewed
  reason
- **THEN** classification SHALL return `excluded` and SHALL NOT assign a metric
  profile or silently treat the path as measured zero

#### Scenario: Classification is missing, ambiguous, or unsupported

- **WHEN** a maintained path matches zero rules, matches multiple rules, or has
  an unregistered governed extension
- **THEN** classification SHALL return the corresponding `unclassified`,
  `ambiguous`, or `unsupported` state with stable matched IDs and a required gap

#### Scenario: Git inventory succeeds

- **WHEN** one tagged Git observation returns present regular tracked and
  non-ignored untracked paths with no parse or object-kind gap
- **THEN** the load SHALL return a non-empty unique stable path tuple and no
  required gaps

#### Scenario: Git inventory is unavailable, malformed, or empty

- **WHEN** Git exits non-zero, command execution raises an OS error, a tagged
  record is invalid, or no present path remains
- **THEN** the load SHALL return no paths and one or more stable required gaps

#### Scenario: A tracked object is not a regular file

- **WHEN** a tracked record declares a symlink, gitlink, unsupported mode, or
  unmerged stage, including an object that is not materialized in the worktree
- **THEN** the load SHALL fail closed from Git record truth before admitting the
  path

#### Scenario: A path is redirected by a symlinked ancestor

- **WHEN** any ancestor component of a tracked or untracked path is a symlink,
  including an ignored ancestor that redirects outside the repository
- **THEN** the load SHALL return no partial inventory and SHALL report the
  symlink-ancestor required gap without following the component

#### Scenario: A declared matcher form is non-canonical or redundant

- **WHEN** a matcher uses trailing `**/*`, adjacent whole-segment `*`/`**`,
  repeated recursive segments, `?`, a character class, a redundant
  exact/`**/basename` pair, redundant extension suffixes, or a terminal suffix
  glob while `extensions` is non-empty
- **THEN** manifest validation SHALL fail under the enumerated canonical dialect
  rather than admit that declared syntax or redundancy

#### Scenario: A legal path resembles an invalid-path label

- **WHEN** a legal Git path has the same text as an invalid path's safe display
  label
- **THEN** explicit `path_state` SHALL preserve both match records and the
  invalid-path required gap without reserving or silently dropping the legal
  path

#### Scenario: Inventory content or digest is forged

- **WHEN** a caller constructs `CarrierMatch` or `CarrierInventory` with an
  invalid path label, empty or unstable IDs/gaps, duplicate or unstable paths,
  incomplete required gaps, altered identity fields, or an arbitrary digest
- **THEN** strict model validation SHALL reject the match or inventory

#### Scenario: A regular tracked path is unstaged-deleted

- **WHEN** a regular tracked index entry is absent from the worktree while other
  present paths remain
- **THEN** the adapter SHALL omit that path as not Git-present and SHALL NOT
  convert unsupported tracked modes into the same non-blocking omission

#### Scenario: Manifest declaration order changes

- **WHEN** semantically identical carrier declarations and input paths are
  presented in a different order or checkout location
- **THEN** the validated manifest and inventory digests SHALL remain identical

### Requirement: Versioned Non-Compensating Metric Contract Registry

The repository SHALL own a separate versioned Budget Contract v2 metric
registry. Each strict immutable contract SHALL bind `contract_id`,
`contract_version`, `metric_id`, `unit`, `carrier_role`, `metric_profile`,
parser identity and version, grammar digest, normalization identity and version,
aggregation, and `non_compensable`. Profiles SHALL resolve every measured
carrier identity to a complete set of contracts for the same role. The loader
SHALL reject unknown fields, duplicate IDs or coordinates, dangling profiles,
invalid digests, non-sum aggregation, compensating coordinates, and
repository-source BPE/model/tokenizer metrics. The registry digest SHALL be
canonical and independent of declaration order.

#### Scenario: A measured carrier resolves its profile

- **WHEN** a measured carrier identity references a valid profile for the same
  role
- **THEN** resolution SHALL return the complete stable-ordered metric contract
  set required by that profile

#### Scenario: A metric contract can compensate or uses model tokens

- **WHEN** a repository-source contract declares `non_compensable = false`,
  non-sum aggregation, or a BPE/model/tokenizer-specific unit or field
- **THEN** strict loading SHALL fail closed and SHALL NOT return an empty clean
  registry

#### Scenario: A profile or coordinate is inconsistent

- **WHEN** a profile references a missing metric, a contract role differs from
  its profile role, or an ID or `(profile, role, metric)` coordinate is
  duplicated
- **THEN** strict loading SHALL report a required gap and SHALL NOT resolve the
  inconsistent profile

#### Scenario: Metric declaration order changes

- **WHEN** semantically identical profiles and contracts are declared in a
  different order
- **THEN** the validated registry digest SHALL remain identical, while any
  parser, grammar, normalization, or other semantic-field change SHALL change it
