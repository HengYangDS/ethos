## ADDED Requirements

### Requirement: Historical Source Budget Replay

ETHOS SHALL replay selected source-budget history from immutable Git blobs and
preserve declared history separately from observed current semantics.

#### Scenario: Immutable v1 baseline drift remains explicit

- **WHEN** the baseline entry is replayed with observer profile
  `v1-continuation-20260719`
- **THEN** the replay subject SHALL be commit
  `2dab77f169eceb2d45f917358c2a7487e7ac8db6` and tree
  `075da5ad45be962e9f5e775b3f050cab4023ea0d`
- **AND** provenance beginning `540e06d5` SHALL NOT be substituted as the replay
  treeish
- **AND** the observer taxonomy SHALL bind commit
  `604934c7afe244caf5b671423f108823a7753a98`, Git blob
  `51a3931b43aa9030e166309289d6d85a80831526`, and content SHA-256
  `b5dfc532586b0e1f3c3f614ce34e70cd9e817b84adfeabfbda266adf19d07a3d`
- **AND** the governed inventory SHALL contain exactly 933 files with SHA-256
  `f8e85ace7648b60592fbe6e678f78169afa98c6289b0e8bb7d7fbc3961fa1c8d`
- **AND** declared v1 total SHALL remain `105342`, replay total SHALL be `105060`,
  and replay drift SHALL be `-282`
- **AND** only JavaScript `89 -> 90`, YAML `1082 -> 800`, and diagram
  `24 -> 23` SHALL differ by category
- **AND** the declaration and historical archive SHALL NOT be rewritten.


#### Scenario: Live Task 4 taxonomy remains a separate unresolved observation

- **WHEN** the same baseline subject is replayed with observer profile
  `v1-live-at-task4-start`
- **THEN** the observer taxonomy SHALL bind commit
  `fe94c0268d060742e808770d4d65d554709af0dd`, Git blob
  `280f4ff640b0d6088c6fc819bebca2c6a7de5fea`, and content SHA-256
  `3180f9739fc254c29fa6ca6924818a2c3eb5d1ccedd0fe1916e88a05e1b41983`
- **AND** the governed inventory SHALL contain exactly 888 files with SHA-256
  `d48fca7255274216d029c600b98972f00bd367b91979441b4d6512a857fb7a5c`
- **AND** global replay SHALL be `104389` with no Jinja coordinate
- **AND** the difference from `v1-continuation-20260719` SHALL be surfaced as an
  unresolved taxonomy-profile disagreement
- **AND** Task 4 SHALL NOT restore live Jinja classification, rewrite the
  historical `-282` correction, or classify the two profiles as clean.

#### Scenario: Selected C1 replay preserves its known blocker

- **WHEN** checkpoint `c1-static-hybrid-accepted` is replayed
- **THEN** its subject SHALL be exact commit
  `3468ce78e2b636b9c0516904aa73cde2eb30fa62`
- **AND** its known YAML adapter gap SHALL remain visible as blocked/unresolved
- **AND** no absent v2 snapshot or provider coverage SHALL be manufactured.

### Requirement: V1 Authoritative V2 Shadow

ETHOS SHALL keep v1 authoritative and v2 inactive while projecting a
fail-closed observer comparison.

#### Scenario: Shadow extends but does not replace v1 report authority

- **WHEN** source-budget reporting includes `v2_shadow`
- **THEN** existing top-level `ok`, `state`, and `required_gaps` SHALL retain
  current v1 semantics
- **AND** `v2_shadow.mode` SHALL equal `v1_authoritative_v2_shadow` and
  `v2_shadow.authoritative` SHALL equal `v1`
- **AND** the shadow SHALL bind observer identity/digests, subject commit/tree and
  snapshot digest, declared/replayed v1 values, v2 coordinates/digests/provider
  coverage or null, disagreements, required gaps, and comparison state
- **AND** any missing observation, adapter failure, provider gap, identity drift,
  replay mismatch, or unresolved disagreement SHALL be classified only as
  `blocked`, `unresolved`, or `reviewed_observation`
- **AND** no Task 4 output SHALL describe v2 as clean, enforced, authoritative,
  cut over, debt-settled, or terminally settled.

### Requirement: Replay Artifact And Tool Boundary

ETHOS SHALL keep raw replay/shadow observations outside tracked repository truth
while providing one declared repository-owned replay command.

#### Scenario: CLI writes ignored raw artifacts and truthful exit status

- **WHEN** the replay CLI executes a configured history entry
- **THEN** history coordinates SHALL come from
  `.config/checks/source-budget/history.toml`
- **AND** raw JSON SHALL be written only under ignored
  `build/evidence/quality/source-budget-v2/replay/`
- **AND** `system/tools.toml` SHALL register the shell owner script rather than
  duplicate command policy
- **AND** invalid config, identity/count/digest mismatch, load/measurement gap,
  or disallowed comparison state SHALL exit non-zero
- **AND** tracked Claim/Chronicle evidence SHALL contain only reviewed summaries
  and digests.
