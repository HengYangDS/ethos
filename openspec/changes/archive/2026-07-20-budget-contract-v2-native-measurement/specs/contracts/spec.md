## ADDED Requirements

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
