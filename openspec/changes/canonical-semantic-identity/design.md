## Context

See `proposal.md` for motivation. The kernel already validates a closed JSON
grammar and renders Commitment and Attestation identity with `_canonical_json`.
However, `canonical_json_digest` bypasses that owner and calls
`json.dumps(sort_keys=True)` directly. Other paths then independently recreate
that operation for proof-floor policy, signed verification payloads, and control
replacement. Rule compilation, skill activation, and source-budget reporting
also emit checksums, but no consumer verifies those fields.

The current `contracts` specification still describes the source-budget
inventory checksum as required even though the terminal direct-measurement
model has no reader for it. Restoring that field would preserve a decorative
identity solely to satisfy stale prose, so this Change retires that clause while
retaining the deterministic inventory observations themselves.

The repository also contains JSON used for different purposes: immutable
content-addressed carrier bytes, exact raw-file hashes, Git programs and
objects, and human/display output. Similar syntax does not make those values the
same semantic concept.

## Goals / Non-Goals

**Goals:**

- Give semantic JSON identity one byte-producing owner in the kernel.
- Make semantic digest and signature consumers use that owner.
- Reject values outside the closed semantic grammar before identity is derived.
- Preserve established Commitment and Attestation domains and canonical bytes.
- Delete duplicate authority-bearing serialization rather than wrap it.

**Non-Goals:**

- No package/module-layout restructuring in this Change.
- No blanket replacement of every `json.dumps` or SHA-256 use.
- No change to raw file, wheel, runtime inventory, Git object, Git transaction,
  or rendered-output byte identity.
- No compatibility serializer, fallback digest, migration registry, or second
  canonicalization schema.

## Decisions

### Classify by meaning before changing code

Serialization sites are classified by the equality proposition their digest
denotes, never by their file, call shape, persistence, or use of JSON:

1. **Semantic identity or admission** — two independently produced typed
   projections are asserted to mean the same thing. Facts, TransitionPlan
   inputs, policy and effect projections, proof-floor policy, independent-
   verification unsigned payloads, and control-replacement subjects make this
   assertion. These consume the one kernel canonical-byte projection.
2. **Content-addressed carrier or exact byte evidence** — wheels, runtime file
   inventories, Git programs, proof artifacts, handoff packages, publication
   request files, and source snapshots. Their identity is the exact carrier or
   native program bytes and remains with that owner unless a later Change proves
   semantic ambiguity.
3. **Presentation projection** — CLI JSON and architecture rendering input.
   Formatting remains a projection concern and cannot define semantic identity.
4. **Unconsumed checksum** — a digest is emitted but no current reader uses it
   for comparison, lookup, signature, CAS, or validation. It owns no invariant
   and is deleted together with schema and documentation that exist only to
   require it.

This prevents a mechanical search-and-replace from erasing meaningful byte
boundaries.

The boundary is compositional. For example, each content and tree-entry hash in
a control snapshot remains an exact Git/file-byte observation, while the outer
typed snapshot that says which paths and observations constitute one control
replacement is a semantic admission projection. Conversely, an adoption write
program or Git update-ref program remains identified by its exact executable
bytes even if JSON-like source data helped construct it.

### Publish canonical bytes from the existing semantic owner

`ethos.contracts.semantic` exposes canonical UTF-8 JSON bytes produced by its
existing closed grammar: null, booleans, safe integers, Unicode strings without
surrogates, arrays, and string-keyed objects. Object keys use UTF-16 code-unit
order, strings are emitted as UTF-8 rather than ASCII escapes, and no whitespace
or trailing newline participates in semantic identity.

`canonical_json_digest` hashes exactly those bytes. Commitment and Attestation
continue to apply their existing schema-version domains to the same bytes; this
Change does not create new identities for them. Consumers may retain a
protocol-specific prefix or domain separator, but they may not redefine the
JSON grammar, key order, string encoding, or whitespace.

Alternative rejected: keep a permissive generic digest for convenience. That
would preserve a second grammar and permit invalid semantic values such as
floating-point numbers to enter admission digests.

### Migrate only proven duplicate semantic owners

Proof-floor consumers use the kernel digest directly and the local
`stable_digest` helper is deleted. Independent-verification receipts expose one
canonical unsigned payload byte method; both `payload_digest` validation and
SSH signature verification consume it. Control-replacement subjects delegate
their outer semantic projection to the kernel owner while retaining all nested
exact-byte hashes. RuleSet and compiled-policy digest fields, the normalized
skill-registry digest, and the source-budget inventory digest are removed
because repository-wide reference analysis found no identity-checking consumer.
The source-budget requirement is narrowed to its directly consumed inventory
and cross-check facts; no replacement checksum or second snapshot is added.

Alternative rejected: move all serializers into a new package. The semantic
boundary must be correct before the later physical-layout batch decides whether
the current module should split. Creating a package now would let file shape,
not responsibility, drive the design.

## Risks / Trade-offs

- **Previously permissive semantic digests may reject floats or invalid Unicode.**
  → These values were already outside the declared semantic grammar; focused RED
  tests make the fail-closed boundary explicit.
- **Non-ASCII semantic projections may receive the correct new digest.** → The
  existing schema contract already specifies this canonical projection. Audit
  the current Attestation set before closeout and prove that no live authority
  depends on bytes produced by the duplicate implementation.
- **A signed external receipt may have been produced with duplicate bytes.** →
  Inspect current validity-bounded receipts before cutover. ASCII-only payloads
  remain byte-identical; any live differing payload must be reissued or receive
  an explicit protocol-version transition rather than silent reinterpretation.
- **A content-addressed carrier may look duplicative but bind exact bytes.** →
  Leave it under its native owner in this Change and record the classification;
  do not replace it without a separate semantic requirement.

## Migration Plan

1. Add failing kernel tests for UTF-16 key order, UTF-8 bytes, and rejection of
   values outside the closed semantic grammar.
2. Add failing consumer tests showing proof-floor, signed receipt, and control-
   replacement identities consume the same canonical bytes where semantic
   equality is asserted; add public-boundary tests that unconsumed checksum
   projections no longer exist.
3. Implement the existing kernel owner and migrate those semantic consumers.
4. Delete `stable_digest` and every equivalent local semantic JSON serializer;
   leave native-byte and presentation owners intact.
5. Audit current Attestations and live signed receipts for compatibility, run
   focused tests and strict OpenSpec validation, then execute the normal exact-
   HEAD closeout route.
