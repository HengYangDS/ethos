## Context

ETHOS already defines projection homomorphism: a presentation may reduce form
but must preserve assertion identity, provenance, bindings, validity, and
absence reason. The former visual source directory implemented those rules, but
its copied semantic model was a parallel tracked owner.

## Decision

ETHOS owns one declaration and its selected terminal-architecture assertion
set. A repository tool reads all bytes with `git show <commit>:<path>`, verifies
the source digests embedded in the semantic graph, constructs complete node and
relation dispositions, and emits canonical compact sorted-key JSON. The output
digest excludes only itself, avoiding self-reference while binding every other
byte and Git identity.

The output is a transport contract, not product authority. It explicitly sets
`effect_authority` to false. Downstream compilers may transform the input into
renderer-neutral IR and artifacts, but cannot reinterpret omitted assertions or
write into ETHOS.

The terminal graph, view quotient, visible copy, and quality contract are new
repository-owned product capabilities, not disposable test scaffolding or
generated evidence. Direct measurement therefore counts every carrier. The
accepted baseline measured 36,971 test ELOC and 88,981 global ELOC; this Change
adds one exact-tree exporter, 174 test ELOC, and 2,005 structured-source ELOC.
The explicit terminal allocation becomes 37,500 test ELOC and 92,000 global
ELOC: the next 500-ELOC test boundary and next 1,000-ELOC global boundary above
the fully counted capability, leaving bounded reserves of 355 and 455 ELOC.
No carrier is reclassified, generated, minified, or excluded, and product,
tool, other-Python, coverage, and per-file constraints remain independently
blocking. Future exhaustion still requires deletion or another explicit product
capability decision; unused allowance is not fungible authority.

## Rejected Alternatives

- Keep the sibling model as authority: preserves a parallel semantic owner.
- Export from the working tree: allows uncommitted host state to contaminate a
  supposedly reproducible projection.
- Embed a fixed commit inside the declaration: creates a self-referential Git
  identity that cannot converge.
- Add an ETHOS lifecycle command: enlarges the product surface for a read-only
  build adapter.

## Failure Semantics

Unknown Git revisions, missing tree paths, path escape, stale source digests,
unknown provenance, incomplete or duplicate dispositions, invalid endpoints,
and claimed effect authority all fail before output is written.
