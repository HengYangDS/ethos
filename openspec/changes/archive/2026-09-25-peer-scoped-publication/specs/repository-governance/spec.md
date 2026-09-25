## ADDED Requirements

### Requirement: Explicit peer-scoped publication

For exact `ethos publish --ref`, callers MAY explicitly select a nonempty
subset of declared peers by ID for that invocation. Omitted selection SHALL
retain the all-peer request; peer health SHALL never select implicitly. ETHOS
SHALL validate the full declared topology, then observe only selected peers
and compile one immutable request binding each selected ID, Git remote, ref,
and exact expected and desired OIDs.

#### Scenario: One declared peer is unavailable

- **GIVEN** GitLab and GitHub are declared and GitLab cannot be observed
- **WHEN** the caller selects only GitHub for an exact publication request
- **THEN** ETHOS may admit and apply the GitHub peer-local transaction without
  observing or mutating GitLab
- **AND THEN** the result identifies GitLab as declared but unselected, not
  published.

#### Scenario: No peer is explicitly selected

- **WHEN** one declared peer is unavailable and the caller supplies no `--peer`
- **THEN** the all-peer request remains unproved and no peer effect begins
- **AND THEN** ETHOS does not silently substitute an available subset.

#### Scenario: Selector is unknown or repeated

- **WHEN** a caller names an undeclared peer ID or repeats one ID
- **THEN** ETHOS rejects the request before remote observation or mutation.

### Requirement: Peer-scoped replay and reporting remain bounded

Before and between remote effects, replay SHALL recheck each selected
ID-to-remote binding and the existing source, proof, ref-role, signature and
exact-CAS obligations. A receipt SHALL NOT accept a new selector or widen its
bound peer set. Results and Attestations SHALL name selected and unselected
peers, and SHALL NOT claim an unselected peer was published.

#### Scenario: Bound peer identity changes before replay

- **WHEN** a receipt's selected peer ID no longer maps to its bound Git remote
- **THEN** replay rejects the receipt before any remote push
- **AND THEN** another declared peer or remote cannot inherit that receipt.

#### Scenario: An existing receipt is given a new selector

- **WHEN** a caller combines `--receipt` with `--peer`
- **THEN** ETHOS rejects the ambiguous request without changing its targets.

#### Scenario: The selected peer itself is unavailable

- **WHEN** the selected peer cannot be observed before an exact-CAS effect
- **THEN** ETHOS reports that selected peer's missing fact and performs no push
- **AND THEN** its continuation preserves the explicit peer selection rather
  than falling back to another peer.

#### Scenario: Release and review roles keep their proof boundaries

- **WHEN** a caller selects one peer for an accepted branch, release branch,
  signed annotated release tag, or proposal ref
- **THEN** the existing role-specific source, signature and proof obligations
  still apply to that selected effect.
