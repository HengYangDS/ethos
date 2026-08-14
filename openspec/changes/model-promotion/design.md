## Context

The product has two semantic roots:

```text
Commitment   immutable normative intent
Attestation  immutable input, observation, judgment, proof, or effect
```

Facts and `TransitionPlan` are derived. The implementation nevertheless retains
parallel intent/progress owners, while Commitment v1 allowed its Python
interpreter to change without a schema-version change. The same carrier bytes
have already produced different semantic digests in installed runtimes.

The terminal model must preserve continuous input without making a Change
unbounded, and make semantic identity independent of runtime defaults.

## Goals

- Exactly two durable semantic roots.
- Same supported-schema bytes always produce the same semantic identity.
- Every relevant input occurrence can be preserved without authorizing effects.
- Unknown predicates, payloads, and relations remain lossless and fail closed.
- Selection is evidence; successor Commitment is normative adoption.
- One Commitment binds one bounded Change, lane generation, and task authority.
- One current Attestation carrier and no mutable ledger or inbox.
- One exact destructive v1-to-v2 bootstrap, then no compatibility path.

## Non-Goals

- A closed ontology for future input.
- Treating text hashes, set membership, selection, tasks, refs, Lease, SQLite, or
  views as normative authority.
- Migrating lifecycle effects beyond Commitment rebind.
- Claiming remote protection or replication for the Attestation ref.

## Decision 1: Commitment V2 Has A Frozen Interpreter

A v2 carrier explicitly writes every identity-bearing field. Omitted Python or
schema defaults never participate in identity. `repository:self` and other
context-dependent aliases are invalid; subjects are explicit.

`schema_version = 2` freezes:

- allowed and required fields;
- tuple ordering and uniqueness;
- path and identifier normalization;
- canonical JSON projection; and
- digest domain.

The wire grammar is closed. Semantic strings and object keys are Unicode
scalar-value sequences. Lone surrogates are invalid and readers never apply
Unicode normalization: canonically equivalent NFC and NFD spellings remain
distinct values. Named fields state separately when empty strings or controls
are forbidden. Identifiers use lowercase ASCII segments separated by `:`;
digests are exactly 64 lowercase hexadecimal characters. Relative path patterns
use `/`, never `.` or `..` segments, NUL, backslash, or a leading slash. Times
use a strict RFC 3339 UTC subset: seconds and `Z` are mandatory, zero fractions
are omitted, non-zero fractions use one to six digits without trailing zero,
and offsets, leap seconds, naive times, and invalid calendar values are rejected.

Canonical JSON is the RFC 8785 string and object-key algorithm over a deliberately
smaller numeric algebra. It is UTF-8 without BOM, trailing newline, or
insignificant whitespace. Its value grammar is `null`, boolean, Unicode string,
I-JSON safe integer
`[-9007199254740991, 9007199254740991]`, array, or object. Floating-point values
are forbidden rather than delegated to a runtime-specific formatter. Object
keys are unique and recursively sorted by RFC 8785 UTF-16 code-unit order; array
order is preserved. Integers use the shortest base-10 spelling without plus
sign or leading zero. `/` and non-ASCII scalars are not escaped; quotation mark,
reverse solidus, and controls use RFC 8785 escapes. Carrier readers reject
duplicate keys, noncanonical member bytes, and unsupported values before model
construction.

The digest is:

```text
SHA256("ethos.commitment.v2\0" || canonical_json(identity_projection))
```

The projection contains intent, subjects, scope, invariants, acceptance, risks,
authority refs, predecessor Commitment digests, selected Attestation IDs, typed
dependencies, typed hypotheses/falsifiers, and typed experiment protocols. All
fields are required in the carrier, including empty collections.

The value contracts and canonical orders are:

- `subjects`, `scope`, `invariants`, `acceptance`, `risks`, and
  `authority_refs`: unique strings sorted by canonical JSON bytes;
- `predecessors` and `selected_attestations`: unique digests sorted
  lexicographically;
- dependency: `{kind, target, attributes}`, sorted by
  `(kind, target, canonical_json(attributes))`;
- hypothesis: `{id, kind, body}`, sorted by `(id, kind,
  canonical_json(body))`;
- falsifier: `{id, hypothesis_id, kind, body}`, sorted by
  `(hypothesis_id, id, kind, canonical_json(body))`;
- experiment protocol: `{id, hypothesis_ids, kind, body}`, where
  `hypothesis_ids` is a unique sorted digest-or-identifier set, sorted by
  `(id, kind, canonical_json(hypothesis_ids), canonical_json(body))`.

Every nested field is required; `attributes` and `body` use the canonical JSON
grammar above. Carrier collections must already be in canonical order; readers
reject rather than silently sort them. Duplicate identity keys or duplicate
complete values fail closed. Changing this interpreter without changing the
version is a contract failure caught by packaged golden vectors.

The Lease retains the minimal exact binding:

```text
(expected_head, expected_tree, carrier_path, SHA256(carrier_bytes), semantic_digest)
```

Loading proceeds in that order: exact bytes, bytes digest, schema version, v2
interpretation, semantic digest, Lease comparison. Plan compilation and effects
occur only afterward.

## Decision 2: Attestation V2 Is Open And Non-Authorizing

An Attestation v2 contains:

- open predicate, verifier, subject, issued time, validity, and closed verdict;
- payload `{kind, body}`, where `kind` is open;
- relations `{kind, target_kind, target_id, attributes}`;
- evidence refs and exact Commitment/Facts/Plan/Policy/Effect bindings; and
- invariant `mints_authority=false`.

Every field is explicit. Optional digest and validity bindings are required
nullable fields and therefore project as `null`, never as an interpreter
default. `advisories` and `evidence_refs` are unique strings sorted by canonical
JSON bytes. Payload is exactly `{kind, body}`. Relation is exactly
`{kind, target_kind, target_id, attributes}`. Kinds and target identifiers use
the identifier grammar above; bodies and attributes use the same canonical JSON
grammar. At least one evidence reference, exact digest binding, or relation is
required.

Relations sort by `(kind, target_kind, target_id, canonical_json(attributes))`
and reject duplicate complete values and duplicate `(kind, target_kind,
target_id)` identity keys.
Identity is:

```text
SHA256("ethos.attestation.v2\0" || canonical_json(all_fields_except_id))
```

Root validation preserves any structurally canonical body. Operation-specific
evaluators decide which predicates, payloads, relations, bindings, and validity
can support a verdict. Unknown values remain queryable but cannot satisfy a
required predicate or authority query.

An input occurrence carries source identity and occurrence coordinates in its
payload. Identical text in different contexts therefore remains distinct. Raw
bytes may be evidence; text digest is never occurrence identity.

## Decision 3: Selection Does Not Adopt

A selection Attestation maps input occurrences to exactly one disposition:

- named semantic owner plus composable relations;
- explicit absence reason;
- contradiction with bound evidence; or
- model gap requiring promotion.

Selection never mutates an active Commitment, Change, scope, acceptance, or task
graph. Contradiction/model-gap predicates block only affected authority queries.

Normative adoption creates a successor Commitment binding predecessor digests
and selected Attestation IDs. It owns one OpenSpec Change, writable lane
generation, and task graph. Independent successors may proceed concurrently
only when dependencies, scopes, and exact effects are disjoint. Moving an
obligation never marks it implemented.

## Decision 4: One Git-Native Attestation Set

The sole current carrier is:

```text
refs/ethos/attestations-set
  -> deterministic parentless commit
  -> canonical Git tree
  -> evidence/attestations/<id[0:2]>/<id>.json
```

The commit uses fixed author, committer, timestamp, encoding, and message, no
parents, and the repository object format. Equal members produce an equal root.
The only mutation is:

```text
new_set = old_set union validated_inputs
```

A writer observes the ref, validates member bytes/path identity, builds the
union tree, and exact-CAS updates the ref. Stale CAS re-observes and recomputes
union. Duplicate bytes are idempotent; different bytes for one ID are an
identity collision. There is no sequence, offset, latest pointer, processed
flag, tombstone, mutable inbox, or reflog semantics.

Git-common JSON directories are staging/cache only after cutover. Existing
tracked Claims, Chronicle, and other historical bytes remain inert Git history
with no current producer, selector, or verdict authority. Current Attestations
are not duplicated onto accepted branch trees.

The public surface is deliberately narrow:

- record one canonical Attestation, or issue one from explicit payload input,
  then CAS-union it into the set;
- query set identity and members by exact semantic filters.

These are projections of the set contract, not workflow or task owners.

## Decision 5: Destructive V1-To-V2 Bootstrap

The existing Commitment rebind family owns the only migration through one
explicit `v1-to-v2-bootstrap` operation. There is no repository-rebind command
or general compatibility reader. Bootstrap derive binds the current v1 Lease
tuple opaquely, reads only the minimal old repository carrier identity and byte
digest through a private bootstrap decoder, validates both exact new v2
carriers, and creates the signed dangling target commit from the exact staged
index. The request binds target tree/head, actor, index, and overlay.

```text
V1_BOUND
  -> exact rebind plan
  -> ref/head CAS
  -> Lease epoch+1 with v2 bytes and digest
  -> effect Attestation
  -> V2_BOUND
```

Bootstrap does not parse v1 with the v2 model or recalculate its digest. It
compares the persisted old lane tuple exactly. Its receipt also binds old and
new repository carrier paths, byte digests, stable repository identity, and the
new v2 semantic digest. Plan compilation, admission, apply, and every recovery
branch use the same opaque-old validator; none call the normal v2 reader for old
bytes. Interruption may recover only to the exact old tuple or exact v2 tuple
plus the effect Attestation in the sole set. Once active v1 generations are
migrated or retired, normal status, plan, prewrite, and mutation reject v1
before plan compilation. The private bootstrap decoder is unreachable from
those readers. Historical v1 bytes remain history only.

The public derive step owns target construction so an operator never runs raw
`commit-tree`, `update-ref`, or SQLite mutation. Apply performs one branch CAS,
one Lease epoch advance, and one Attestation-set union. Recovery re-observes
those exact three carriers and returns one typed continuation; operation-local
JSON may stage request bytes but is not current evidence authority.

## Decision 6: Parallel Authorities Are Removed

Useful meanings map into the two roots:

- normative intent, hypothesis, protocol, dependency -> Commitment;
- input, observation, evaluation, selection, decision, proof, effect ->
  Attestation payload/predicate/relation;
- progress -> one OpenSpec Change task graph;
- current coordination -> fresh Facts and local Lease fencing;
- historical bytes -> inert Git history.

Claim/Chronicle readers, evolution ledger, Campaign state, shared inbox state,
reusable permissions, and operation-specific current Attestation indexes are
removed. No compatibility facade or dual reader remains.

## Alternatives Rejected

- **Append to active Change:** loses bounded closure.
- **Mutable inbox, ledger, Campaign, or Chronicle:** creates another currentness
  and progress authority.
- **Text-hash deduplication:** collapses distinct occurrences.
- **Closed relation/payload enums:** cannot preserve future valid input.
- **Accepted-branch Attestation files:** every input mutates protected trees.
- **Several operation-specific stores:** duplicates selection/currentness.
- **Long-lived v1/v2 readers:** preserves the ambiguity being removed.

## Verification

- Golden vectors run from source, built wheel, and package-only runtime.
- Mutating a v2 default/interpreter without a version bump fails vectors.
- Property tests cover relation ordering, duplicate rejection, opaque
  round-trip, non-authorizing selection, set-union commutativity/idempotence,
  and stale-CAS retry.
- Real local Git tests prove deterministic parentless roots and collision safety.
- Bootstrap interruption tests permit only exact `V1_BOUND` or `V2_BOUND` plus
  effect Attestation.
- Architecture/residue tests prove no active Claim, Chronicle, Ledger, Campaign,
  shared-inbox, v1, or duplicate Attestation authority remains.
- OpenSpec strict validation, focused gates, code/ponytail review, exact-HEAD
  full proof, archive, post-archive proof, and governed closeout complete
  acceptance.
