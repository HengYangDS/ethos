## Context

DR-0008 and the accepted Budget Contract v2 design require native metric
domains, content-addressed observations, deterministic aggregation, and
fail-closed parser behavior. Task 2 delivered exact-one carrier classification
and metric declarations but intentionally stopped before opening carrier bytes.

The current metric registry also exposes two implementation-time mismatches.
Several providers are labelled only stdlib-3.14 even though ETHOS packages
run on Python 3.12+, which does not distinguish the package runtime from the
measurement runtime or bind patch/library behavior. The shell carrier also
includes Bash and Zsh source while its provider is labelled posix-v1. T3 must
declare a separate canonical CPython 3.14 measurement runtime, exact provider
algorithm versions, dependency majors, and a startup conformance fingerprint
rather than ignore runtime fields or claim cross-minor equivalence. PyYAML is
already direct, but its admitted provider contract is major-version-bound and
the package constraint must therefore stay below 7.

The candidate base subsequently retired the adoption scaffold's Jinja renderer,
packaged templates, carrier, metric, and dependency while replacing the one
surviving typed TOML leaf with `tomli-w`. T3 does not reverse that adoption
decision. It re-admits Jinja2 under a distinct product-source boundary: the
provider parses bytes for measurement, the `template_source` carrier is owned by
`ethos-product`, and no adoption render environment or scaffold template returns.

The prior minimal-adoption archive declared the new `Minimal Adoption Binding`
as a modification even though canonical truth still named `Adoption Scaffold`.
That incomplete promotion also left historical profile, overlay, provider-CI,
and rendering obligations active. T3 repairs only the canonical projection
through an explicit repository-governance delta; it does not rewrite the dated
archive or restore a retired adoption mode. The only runtime hardening in this
reconciliation lets missing or non-directory explicit roots reach the existing
`git_repository_missing` admission gap instead of escaping before JSON output.

The current external-adopter observation is deliberately narrower than the
retired overlay-era records. It measures one-binding creation and conflict
preservation in neutral isolated Git clones. A synthetic clone has no adopter
native backend, so this Change records native/external parity as not performed
rather than manufacturing a parity claim from two invocations of the product
runtime. Native-backend parity remains a separate evidence exercise with its own
adopter-owned execution surface and verifier.

Removing the adoption renderer also removed the package's former static Jinja
import. Native measurement intentionally keeps the parser lazy so an unavailable
provider becomes a stable gap instead of preventing module import. Dependency
hygiene therefore records one exact `DEP002=jinja2` package rule in both its
policy and runner, with an architecture test that forbids widening the exception.

## Goals / Non-Goals

**Goals:**

- Bind each worktree measurement to bytes read through descriptor-relative
  no-follow traversal and reject object drift.
- Define strict frozen, self-verifying native, carrier, coordinate, and snapshot
  models plus XOR load envelopes.
- Dispatch only from an exact provider signature, canonical CPython 3.14
  runtime, and passing runtime conformance fingerprint; make every grammar
  digest reproducible from a repository-owned canonical descriptor.
- Define deterministic lexical, structured, template, footprint, shell, and C4
  measures that resist line packing, minification, giant-payload laundering,
  and cross-domain disappearance.
- Make one-file failure invalidate the complete carrier or snapshot result.
- Preserve v1 authority and keep T4+ replay, policy, and enforcement inactive.

**Non-Goals:**

- Claim a cross-file atomic snapshot, Git blob OID, index identity, or HEAD
  identity. T2 does not retain those facts; T4 owns immutable Git observation.
- Add a model/BPE tokenizer, execute shell/Python/template content, or render
  Jinja.
- Change v1 gates, reports, baselines, allowances, debt, campaigns, commands, or
  publication state.
- Treat OS inode/timestamp metadata as persistent observation identity.
- Admit every package-supported Python minor as a successful measurement
  runtime. A later contract may add another canonical runtime after its own
  conformance evidence.

## Decisions

1. **Module topology and public API.** Core immutable contracts live in
   ethos_core.contracts.source_budget.measurements. Context-bound load
   admission and compact canonical digest helpers live in
   measurement/admission.py and measurement/canonical.py as implementation
   support, not product API. Repository orchestration lives in
   measurement/core.py; pure native parsing is split into
   measurement/native/core.py, measurement/native/_structured.py, and the
   semantic `measurement/native/shell/` subpackage. That subpackage contains
   only `core.py` and `grammar.py`; its `__init__.py` is declaration-only.
   Canonical model construction is owned by
   NativeMeasurement.create, CarrierMeasurement.create, and
   MeasurementSnapshot.from_inventory; no top-level build/digest helper is a
   public contract. The product public API is:

       measure_native(
           content: bytes,
           contracts: tuple[MetricContract, ...],
       ) -> NativeMeasurementLoad

       measure_carrier(
           root: Path,
           match: CarrierMatch,
           contracts: MetricContractSet,
       ) -> CarrierMeasurementLoad

       measure_snapshot(
           root: Path,
           inventory: CarrierInventory,
           contracts: MetricContractSet,
       ) -> MeasurementSnapshotLoad

2. **Strict self-verifying contracts.** MetricValue, NativeMeasurement,
   CarrierMeasurement, MeasurementCoordinate, and MeasurementSnapshot are
   frozen Pydantic models with extra fields forbidden. Public constructors
   require unique stable order, non-negative integer values, complete required
   coordinates, and recomputed digests. NativeMeasurementLoad,
   CarrierMeasurementLoad, and MeasurementSnapshotLoad are frozen slotted
   dataclasses with an exact XOR: either an exact concrete typed success and no
   gaps, or no success and a non-empty sorted unique built-in tuple of exact
   strings. Load envelope types forbid subclassing. Success data must equal its
   fully revalidated form, and the Load stores that canonical revalidated model
   rather than the caller-owned instance. Bare Pydantic validation proves only
   internal structure and digest consistency. Carrier success Load
   admission additionally requires the exact CarrierMatch and MetricContractSet
   as initialization-only context and replays CarrierMeasurement.create;
   snapshot success Load admission requires the exact CarrierInventory and
   MetricContractSet and replays MeasurementSnapshot.from_inventory. The
   context is neither retained nor hashed and must use the exact concrete model
   types rather than mappings or subclasses. Missing, forged, mismatched, or
   context-free success fails closed, and failure Loads forbid success context.
   Every success therefore carries an empty gap tuple; every failure carries no
   success and a sorted, deduplicated non-empty exact tuple of stable gaps.
   NativeMeasurementLoad remains context-free because NativeMeasurement embeds
   and verifies its complete resolved contracts.

3. **Two digest planes.** content_sha256 binds exact raw bytes.
   normalized_digest and metric values bind the provider-normalized stream.
   A carrier/snapshot identity digest includes relative path, complete carrier
   identity, raw content digest, metric-contract-set digest, and native result.
   A separate vector digest binds sorted coordinates and normalized values.
   Therefore CRLF and LF may have equal normalized values/vector digest while
   their raw content and observation digests remain different. Absolute paths,
   traversal order, locale, time, device, inode, mode timestamps, and read-time
   fingerprints never enter persistent digests.

4. **Descriptor-bound worktree reads.** Open the repository root descriptor,
   traverse every ancestor with O_DIRECTORY plus O_NOFOLLOW, and open the final
   component with O_NOFOLLOW plus O_NONBLOCK so a FIFO cannot block before
   fstat. Require a regular final file, keep the complete descriptor chain until
   the read finishes, and compare device, inode, mode, size, mtime_ns, and
   ctime_ns before and after reading. Then use parent dir_fd lookups with
   follow_symlinks=False to reverify every ancestor entry and the final entry
   against their opened device/inode/mode identity. Any open/read/stat failure,
   symlink, non-directory ancestor, non-regular final object, short or changing
   object, path-entry replacement, or fingerprint drift returns a stable
   required gap and discards all bytes and partial metrics. Every opened
   descriptor is closed on every exit path. `MemoryError`, `RecursionError`, and equivalent local
   resource exhaustion map to stable non-sensitive provider or carrier gaps;
   exception text and absolute paths never cross the boundary. These
   fingerprints are ephemeral race checks only.

5. **Canonical runtime and provider signatures.** Successful native
   measurement is admitted only under CPython 3.14. Package import and other
   ETHOS commands remain supported on Python 3.12+, but a non-canonical
   measurement runtime returns a stable required gap. Dispatch uses the exact
   tuple of runtime contract, parser id/version, grammar digest, normalization
   id/version, metric id, and unit. Provider versions are explicit per governed
   algorithm: the corrected shell grammar uses `ethos-shell-v4`, YAML uses
   `ethos-yaml-v2`, Jinja uses `ethos-jinja-v3`, and unchanged native providers
   retain v1. Jinja and PyYAML signatures additionally bind their admitted major
   versions; repository-owned providers bind their algorithm plus the canonical
   runtime.

   Every provider descriptor contains the canonical runtime identity, admitted
   dependency majors, algorithm rules, a conformance corpus digest, and expected
   output digest. The expected output digest is a reviewed repository constant;
   it is never recomputed from the current implementation at startup. Before
   serving measurements, a cached startup self-test runs the fixed corpus through
   all provider primitives and compares the result with the descriptor
   fingerprint. Wrong Python implementation/minor, dependency
   major, missing provider, or conformance mismatch fails closed. Multi-provider
   startup gaps are sorted and deduplicated before exposure. Grammar digests are
   SHA-256 over compact canonical descriptor JSON, and any altered signature is
   rejected. Parser rules and corpus are finalized first; reviewed output
   constants are updated second; grammar digests and every matching policy atom
   are updated last in one Change. A patch upgrade may be admitted without changing
   metric identity only when it produces the exact conformance fingerprint;
   otherwise a new governed provider version is required.

6. **Text and newline normalization.** All text providers accept bytes, require
   strict UTF-8, remove one leading UTF-8 BOM, normalize CRLF and CR to LF, and
   reject invalid UTF-8 or embedded BOM ambiguity. Raw SHA-256 is computed
   before normalization. Footprint and control providers measure the normalized
   UTF-8 bytes directly.

7. **Python lexical semantics.** Use stdlib tokenize over normalized UTF-8 and
   ast.parse only as a syntax-validity guard. Exclude ENCODING, ENDMARKER, NL,
   NEWLINE, INDENT, and DEDENT; include substantive tokens and comments. Reject
   ERRORTOKEN, tokenizer failure, or AST failure. lexical_tokens is the
   significant-token count. normalized_bytes is the UTF-8 length of a
   length-framed canonical stream of token type and spelling. This is invariant
   to non-substantive whitespace while remaining sensitive to identifiers,
   literals, comments, and statement separators. Semicolon packing is not
   claimed to
   be byte-for-byte equivalent to newline separation: the separator remains a
   substantive token, so packing cannot reduce the lexical or normalized-byte
   coordinate and cannot launder an ELOC reduction.

8. **Structured semantics.** TOML uses tomllib; JSON uses duplicate-detecting
   object pairs and rejects NaN/Infinity; YAML uses a restricted SafeLoader
   that rejects duplicate keys, non-core or dangerous tags, aliases/anchors
   that can create shared/cyclic graphs, multiple documents, and non-finite
   values; INI is strict and disables interpolation. The restricted YAML loader
   accepts only YAML 1.2 or an absent version directive and rebuilds the complete
   Core scalar resolver and constructors instead of inheriting PyYAML 1.1 rules.
   Leading-zero decimals, `0o` octal, `0x` hexadecimal, and exponent floats use
   Core numeric semantics; legacy booleans, sexagesimal values, underscored
   numbers, binary forms, signed hexadecimal, timestamp-looking text, merge
   tokens, and value tokens remain strings unless an exact admitted explicit tag
   applies. Explicit bool/int/float/null tags must themselves use an admitted Core
   lexical form. YAML mapping-key uniqueness compares scalar tag plus canonical
   scalar frame. Tag-distinct values that Python compares equal (`true`/`1`,
   `1`/`1.0`, and `-0.0`/`0.0`) remain distinct typed entries; same-tag canonical
   equivalents such as `0xB`/`11` fail closed. The loader retains typed entry
   storage rather than inserting those keys into a lossy Python dictionary.
   Every parsed value is canonicalized with explicit scalar type framing and
   sorted mapping keys. semantic_nodes counts containers, mapping
   keys, and scalar values. normalized_scalar_bytes counts canonical scalar
   frames, so formatting and declaration order do not change the vector.

9. **Template semantics.** Jinja is parsed, never rendered. Dynamic units are
   counted from the validated AST excluding the root and static TemplateData
   nodes. `template_dynamic_bytes` is the byte length of the canonical validated
   dynamic-AST payload, so equal node counts cannot launder larger dynamic
   literals. Non-finite numeric AST leaves are rejected before canonicalization,
   and canonical JSON forbids NaN/Infinity defensively. Static payload bytes come
   from lexer data and comment payload tokens
   after newline normalization, so a giant comment cannot become a zero-vector
   payload. Dynamic units, canonical dynamic bytes, and static/comment bytes are
   three non-compensating coordinates.

   The carrier identity is `jinja-templates` with role `template_source`, scope
   `product.templates.jinja`, and owner `ethos-product`. Restoring this typed
   classification and parser does not restore adoption rendering and does not
   by itself admit a new tracked template extension through the format gate;
   adding an actual template carrier still requires its own current format and
   execution owner.

10. **Shell and C4 semantics.** Shell v4 is a repository-owned finite lexical
    grammar covering governed Bash/Zsh constructs: quoting, escapes, comments,
    operators, explicit function-header and brace lifecycle, phase-aware case
    subject/pattern/body/closure state, literal reserved spellings, literal and
    regex dollar anchors, parameter/command/arithmetic substitutions including
    Zsh `${(j:,:)items}`, arithmetic shifts, assignment fragments, arrays including
    parameter-length forms, double brackets, process substitution, numeric-FD and
    repeated redirections, validated backtick substitutions inside double quotes,
    line-continuation command state, context-sensitive adjacent closers for nested
    command, process, quoted, and arithmetic substitutions, and heredocs including quote-removed but
    non-expanded delimiter fragments and bodies nested inside command substitutions.
    Every word scanner has a no-progress guard; unterminated or incompatible states
    fail closed rather than loop. Recursion exhaustion is classified as the stable
    resource-exhausted gap rather than a syntax failure. It is not shlex, a regex proxy, or a claim of
    complete shell execution semantics. The C4 provider is a
    finite scanner and statement grammar for comments plus system, container, and
    rel records with quoted payloads and exact arity. Unknown statements or
    malformed quoting fail.

11. **Snapshot aggregation and exclusions.** A snapshot accepts only a valid,
    gap-free, self-verifying CarrierInventory. MeasurementSnapshot.from_inventory
    derives the manifest/inventory digests and exact classified path/identity set
    from that inventory; it does not accept or persist match/exclusion counts.
    Reviewed counts are adapter/Chronicle report-only values recomputed from the
    same validated inventory and do not enter the snapshot schema or canonical
    digests. The Task 2 contract already makes an empty inventory a required gap,
    while an all-reviewed-exclusion non-empty inventory may produce an empty
    vector. Direct measure_carrier accepts
    only state=classified with disposition=measure; direct excluded input
    returns a stable excluded-carrier gap rather than a zero. measure_snapshot
    measures classified matches in canonical repository-relative order, skips
    reviewed state=excluded matches, and rejects every other state. It always
    binds the complete input manifest_digest and inventory_digest, so every
    excluded path and identity remains part of snapshot identity even though it
    contributes no coordinate.

    Coordinates aggregate by scope id, metric id, and unit. Reversing input
    order cannot change output. Any invalid match, missing provider, parser
    failure, content drift, a duplicate coordinate inside one native result or
    forged snapshot output, or one-file failure returns no snapshot plus complete
    stable gaps; no partial vector is exposed. Multiple carriers contributing to
    the same scope/metric/unit are valid and are summed. Moving
    identical bytes to another measured carrier changes coordinate domain;
    moving them to a reviewed exclusion removes the coordinate but changes the
    complete inventory and snapshot identity rather than disappearing. The
    current GitLab CI YAML uses anchors/aliases rejected by the approved YAML
    provider; T3 records that deterministic provider gap in complete-inventory
    evidence and does not weaken graph safety to manufacture a clean snapshot.

12. **Test corpus isolation.** All adversarial cases are encoded in
    tests/fixtures/source-budget-v2/cases.toml as logical filenames plus UTF-8
    text or hexadecimal bytes. Tests materialize target suffixes under tmp_path.
    This keeps fixtures in the test-TOML domain, prevents invalid bytes or line
    ending conversion by Git, and avoids expanding production carrier rules.

13. **T3/T4 boundary.** T3 binds one descriptor-read file at a time and creates
    a deterministic aggregate over successful reads; it does not claim
    simultaneous cross-file immutability. Git blob OID, tracked/index identity,
    immutable batch reads, baseline replay, and historical observations remain
    T4. T3 does not activate v2 policy, command/gate routing, shadow mode, or
    enforcement.

## Risks / Trade-offs

- [Object changes during reading] -> compare pre/post descriptor state and
  discard the complete result on drift.
- [Symlinked ancestor escapes the root] -> traverse each component by descriptor
  with no-follow semantics and never resolve a user path.
- [Library/runtime change silently changes metrics] -> canonical CPython 3.14
  runtime, exact provider descriptor/signature, bounded dependency major, and a
  startup conformance fingerprint that fails closed.
- [Parser returns unsafe or partial data] -> reject duplicate, non-finite,
  aliased/cyclic, tagged, multi-document, or unsupported data first.
- [Native parsing exhausts local resources] -> map exhaustion to stable gaps,
  close descriptors deterministically, keep v2 inactive, and require either a
  versioned `max_carrier_bytes` contract or admitted isolated execution before
  activation.
- [Finite shell grammar is mistaken for an executor] -> keep it lexical, never
  execute input, enumerate admitted constructs, and fail unknown states.
- [Raw and normalized identity are conflated] -> separate raw content,
  normalized, vector, carrier, and snapshot digests.
- [One native module exceeds the active 500 effective-LOC logic limit in
  .ethos/rules.toml] -> keep dispatch/normalization and structured grammar
  separate, and keep Shell in the two-module semantic `native/shell/` subpackage;
  run code-size and module-layout owner gates over Git-visible files.
- [Fixtures alter production inventory] -> one TOML test carrier, with runtime
  materialization only.
- [T3 overclaims Git identity] -> HEAD/blob identity and atomic Git snapshots
  stay in T4.

## Migration Plan

1. Commit this governance carrier and corrected Task 3 topology.
2. Add RED kernel tests for strict models, XOR envelopes, coordinate
   completeness, stable order, and digest forgery.
3. Implement the measurement contract module and make kernel tests GREEN.
4. Add RED native/provider tests, including canonical-runtime rejection,
   runtime conformance fingerprint, live registry correction, and dependency
   major boundaries.
5. Implement exact runtime/provider dispatch, canonical descriptors,
   conformance self-test, native parsers, and normalizers; update metric policy
   identities and lock metadata.
6. Add RED descriptor and snapshot tests for symlinks, same-size rewrite,
   pre/post drift, reversed order, domain movement, and whole-result rejection.
7. Implement descriptor-bound carrier reads and deterministic aggregation.
8. Run the complete inventory twice in opposite order and retain reviewed
   summary/digest evidence only.
9. Run focused 100 percent statement/branch coverage, v1 regressions,
   lint/config/schema/dependency/module-layout/source-budget, strict
   OpenSpec/claims/lifecycle, parity, independent review, and exact-HEAD proof.
10. Complete official archive inputs. Archive-HEAD parity/proof, candidate land,
    accepted-root closeout, local publication readiness, and owned-Lane
    retirement remain separate transitions.

Rollback before land reverts T3 contracts, providers, registry signatures, and
the PyYAML upper bound together while leaving v1 authoritative. An archived
Change is never rewritten.

## Open Questions

None. Calibrated values, immutable Git replay, policy, enforcement, cutover, and
v1 global LOC retirement remain assigned to later Changes.
