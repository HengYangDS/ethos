## MODIFIED Requirements

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
