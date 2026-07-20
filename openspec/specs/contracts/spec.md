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

The repository SHALL own a strict versioned Budget Contract v2 carrier manifest. It SHALL classify every Git-present path as one measured identity or reviewed exclusion, evaluate all rules without priority, and fail closed on invalid, duplicate, or noncanonical declarations; missing, ambiguous, or unsupported matches; unsafe Git state; partial inventory; or forged identity or digest. Inventory and digests SHALL be stable across ordering, locale, timezone, and checkout location.

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

The repository SHALL own a separate versioned strict Budget Contract v2 metric registry. Each measured carrier SHALL resolve to a complete same-role, stable set of non-compensating native metric contracts. The loader SHALL reject unknown fields, duplicate IDs or coordinates, dangling or cross-role profiles, invalid digests, non-sum aggregation, compensation, and repository-source BPE, model, or tokenizer metrics. The registry digest SHALL be canonical and declaration-order independent.

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

### Requirement: Content-Bound Native Source Measurement

ETHOS SHALL measure a Budget Contract v2 carrier only through a versioned,
repository-owned native provider whose complete parser, grammar, normalization,
metric, and unit signature matches the declared metric contract. A worktree
observation SHALL bind exact raw content identity separately from normalized
metric identity and SHALL fail closed when content cannot be read and parsed
without ambiguity.

#### Scenario: A regular carrier is bound to descriptor-read bytes

- **WHEN** ETHOS measures a classified worktree carrier
- **THEN** it SHALL traverse every path component relative to the repository descriptor without following symlinks
- **AND** the final open SHALL be non-blocking before regular-file admission, and the opened ancestor/final path entries SHALL be reverified after reading
- **AND** it SHALL require a regular final object and compare descriptor state before and after reading
- **AND** every opened descriptor SHALL be closed on every success or failure path
- **AND** its persistent observation SHALL bind repository-relative path, carrier identity, raw content SHA-256, metric-contract-set digest, normalized result, and measurement digest
- **AND** a provider success whose embedded raw content SHA-256 does not equal the descriptor-read bytes SHALL be rejected even when that provider result is otherwise internally valid
- **AND** device, inode, timestamps, locale, absolute root, and traversal time SHALL NOT enter the persistent digest.

#### Scenario: Provider identity binds a canonical runtime

- **WHEN** a native provider is selected
- **THEN** dispatch SHALL require the declared CPython 3.14 measurement runtime and SHALL match parser id/version, grammar digest, normalization id/version, metric id, and unit
- **AND** the provider descriptor SHALL bind admitted dependency majors, a conformance corpus digest, and a reviewed constant expected conformance output digest that startup SHALL NOT derive from the current implementation
- **AND** startup conformance SHALL fail closed for the wrong implementation or minor, a missing or wrong dependency major, or changed provider behavior
- **AND** the grammar digest SHALL be reproducible from the canonical repository-owned provider descriptor
- **AND** an unavailable, unknown, altered, or runtime-incompatible provider SHALL produce a required gap rather than zero
- **AND** model-specific or BPE tokenizer identity SHALL NOT be admitted as repository-source truth.

#### Scenario: Native measures resist representation games

- **WHEN** valid Python, shell, structured declaration, template, control, documentation, evidence, or C4 content is measured
- **THEN** programming source SHALL produce significant lexical tokens and canonical normalized bytes
- **AND** semicolon statement packing SHALL NOT reduce either Python coordinate relative to equivalent newline-separated statements
- **AND** structured declarations SHALL produce semantic nodes and canonical scalar bytes independent of pretty printing or declaration order
- **AND** Jinja SHALL be parsed without rendering, SHALL reject non-finite numeric AST leaves, SHALL use strict canonical JSON, and SHALL separately emit dynamic AST units, canonical dynamic AST payload bytes, and static data/comment payload bytes
- **AND** those three Jinja coordinates SHALL be non-compensating, so equal node counts SHALL NOT hide larger dynamic literals and static/comment bytes SHALL NOT offset dynamic growth
- **AND** the parse-only provider SHALL bind a product-owned `template_source` carrier without restoring adoption scaffold templates or an adoption rendering surface
- **AND** the measurement classifier SHALL NOT by itself admit a new tracked template extension without a separately governed format and execution owner
- **AND** one leading UTF-8 BOM and newline convention SHALL be normalized only for provider values while the raw content digest remains exact.

#### Scenario: Finite shell and YAML grammars preserve admitted semantics

- **WHEN** governed shell or YAML source is measured
- **THEN** Shell v4 SHALL track command, function-header, case subject/pattern/body/closure, group, redirection, and heredoc state explicitly
- **AND** shell arithmetic shifts SHALL remain arithmetic rather than heredoc operators, case keywords SHALL be interpreted only in the matching case phase, reserved spellings outside reserved-word position SHALL remain word text, Zsh `${(j:,:)items}` SHALL remain a parameter expansion, quote-removed heredoc delimiter fragments SHALL NOT be expanded, and an unterminated backtick inside double quotes SHALL fail closed
- **AND** adjacent nested command, process, quoted, and arithmetic substitution closers SHALL be selected from active group context rather than longest-prefix text alone
- **AND** a scanner iteration that cannot advance SHALL fail closed rather than loop
- **AND** YAML SHALL use complete YAML 1.2 Core scalar resolution with strict bool/int/float/null constructors and SHALL reject a non-1.2 version directive
- **AND** YAML mapping-key uniqueness SHALL compare scalar tag plus canonical scalar frame, preserve tag-distinct Python-equal keys in typed storage, and reject same-tag canonical duplicates
- **AND** PyYAML 1.1 boolean, octal, sexagesimal, binary, underscored-number, timestamp, merge, value, or yaml-tag resolution SHALL NOT leak into the provider identity
- **AND** provider semantic changes SHALL update parser version, conformance constant, grammar digest, and every matching metric contract atomically.

#### Scenario: Unsafe or invalid input fails closed

- **WHEN** content has invalid UTF-8, parser failure, duplicate structured keys, non-finite values, unsafe YAML tags or graph structure, malformed Jinja, unterminated shell constructs, malformed C4 records, or a grammar/version mismatch
- **THEN** ETHOS SHALL return no native or carrier measurement
- **AND** local memory or recursion exhaustion SHALL map to a stable resource-exhausted gap without exception text, descriptor data, absolute paths, or partial coordinates
- **AND** it SHALL return stable non-empty required gaps without library exception text or partial coordinates.

### Requirement: Deterministic Fail-Closed Measurement Aggregation

ETHOS SHALL aggregate Budget Contract v2 measurements as a non-compensating,
self-verifying vector whose result is independent of input order and whose
success is impossible when any required carrier result is missing or invalid.

#### Scenario: Reversed input order produces one identity

- **WHEN** the same valid carrier inventory is measured in forward and reversed order
- **THEN** carrier results SHALL be sorted by canonical repository-relative identity
- **AND** coordinates SHALL be aggregated and sorted by scope id, metric id, and unit
- **AND** normalized vector and snapshot digests SHALL be identical for the same exact byte set.

#### Scenario: One failed carrier invalidates the snapshot

- **WHEN** any carrier is unclassified, ambiguous, unsupported, unreadable, changed during reading, missing a required metric, or rejected by its provider
- **THEN** the measurement snapshot SHALL be absent
- **AND** all stable required gaps SHALL be reported
- **AND** no clean partial vector or digest SHALL be exposed.

#### Scenario: Persisted success loads replay authoritative context

- **WHEN** ETHOS loads a persisted carrier or snapshot success
- **THEN** bare model validation SHALL establish internal structure and digest consistency only
- **AND** success data and admission context SHALL be exact concrete model types, the Load SHALL store only the fully revalidated canonical success model rather than the caller-owned instance, failure gaps SHALL be an exact built-in tuple of exact non-empty strings, and Load envelope types SHALL NOT be subclassable
- **AND** carrier success admission SHALL require the exact classified match and metric-contract registry and SHALL replay canonical carrier construction to the identical result
- **AND** snapshot success admission SHALL require the complete carrier inventory and metric-contract registry and SHALL replay canonical snapshot construction to the identical result
- **AND** the admission context SHALL be initialization-only and SHALL NOT enter the persisted model or digest
- **AND** context-free, missing, forged, or mismatched success context SHALL fail closed, while a failure load SHALL forbid success context
- **AND** native success loading MAY remain context-free because the native result embeds and verifies its complete resolved metric contracts.

#### Scenario: Load and startup gaps cannot be laundered into success

- **WHEN** a native, carrier, or snapshot Load is constructed or multiple provider startup failures are observed
- **THEN** an exact concrete success SHALL require an empty exact built-in gap tuple
- **AND** a failure SHALL carry no success plus a non-empty exact tuple of exact strings
- **AND** exposed gaps SHALL be sorted and deduplicated canonically
- **AND** success data accompanied by any gap, partial vector, forged provider result, or noncanonical gap container SHALL fail closed.

#### Scenario: Reviewed exclusions remain in snapshot identity

- **WHEN** a valid carrier inventory contains both classified and explicitly excluded matches
- **THEN** measure_snapshot SHALL measure only classified measured carriers and SHALL skip reviewed exclusions
- **AND** direct measure_carrier on an excluded match SHALL return a required gap rather than a zero measurement
- **AND** canonical snapshot construction SHALL derive the classified path/identity set from the complete gap-free inventory and SHALL NOT accept or persist match/exclusion counts; any reviewed counts SHALL be report-only values recomputed from that inventory
- **AND** the snapshot SHALL bind the complete manifest and inventory digests so excluded path movement or identity changes remain observable.

#### Scenario: Domain movement remains visible

- **WHEN** identical bytes move to a different carrier, role, or scope
- **THEN** the carrier and snapshot identity SHALL change
- **AND** the value SHALL be aggregated only in the new measured coordinate domain
- **AND** movement into a reviewed exclusion SHALL remove the coordinate but SHALL change the bound inventory and snapshot identity
- **AND** tests, product source, templates, evidence, derived projections, governance history, and documentation SHALL NOT compensate for one another.

#### Scenario: Measurement remains inactive during T3

- **WHEN** T3 native measurement is present
- **THEN** v1 source-budget policy and report routing SHALL remain authoritative
- **AND** v2 activation SHALL require a separately reviewed versioned carrier-byte ceiling or admitted isolated-execution boundary
- **AND** immutable Git replay, v2 shadow output, policy, Debt v2, changed-scope admission, dual control, cutover, and v1 global LOC retirement SHALL remain inactive until their governed Changes.
