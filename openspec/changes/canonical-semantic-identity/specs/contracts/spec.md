## MODIFIED Requirements

### Requirement: Direct Source Measurement Contract

ETHOS SHALL expose one direct, fail-closed repository source measurement report
without a carrier-model hierarchy, metric registry, worker protocol, snapshot or
replay runtime, shadow model, or debt contract.

#### Scenario: The measurement policy is loaded

- **WHEN** ETHOS loads `.config/checks/format/selection.toml`
- **THEN** it requires non-compensating role ceilings and a jointly derived
  global ceiling, one bounded `scc` command with exact non-negative tolerances,
  a fixed canonicalization line width, named aggregate members, and admitted
  format budget rows
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
  mode while classifying each file
- **AND** each admitted path is classified once by declared extension and
  optional path patterns, or by a declared shebang when an executable has no
  extension
- **AND** a Git-present executable that has neither an admitted extension nor an
  admitted shebang produces a required unclassified-executable gap
- **AND** the report exposes the directly consumed file count, category counts,
  measurements, and independent cross-check rather than an unconsumed inventory
  checksum.

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
