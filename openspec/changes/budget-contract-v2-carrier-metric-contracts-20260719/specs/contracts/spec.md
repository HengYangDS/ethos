## ADDED Requirements

### Requirement: Typed Source Budget Carrier Manifest

The repository SHALL own a versioned Budget Contract v2 carrier manifest whose
strict immutable models classify every maintained Git-present path as exactly
one measured carrier identity or one explicit reviewed exclusion. The loader
SHALL reject unknown fields, duplicate identities or matcher identities, empty
or invalid repository-relative POSIX matchers, and invalid
measure/exclusion combinations. Classification SHALL evaluate every rule without
priority or first-match semantics and SHALL report zero matches, multiple
matches, or unsupported governed extensions as required gaps. The manifest and
inventory digests SHALL be deterministic under declaration order, path
enumeration order, locale, timezone, and absolute checkout location.

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
