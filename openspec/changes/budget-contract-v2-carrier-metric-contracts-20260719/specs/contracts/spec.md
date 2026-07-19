## ADDED Requirements

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
