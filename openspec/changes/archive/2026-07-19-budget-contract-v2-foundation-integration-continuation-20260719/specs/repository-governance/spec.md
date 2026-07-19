## ADDED Requirements

### Requirement: Archived Work Lane candidate-drift continuation

ETHOS SHALL continue useful work from an archived or historically proved Work
Lane through an owned, claim-bound successor based on the latest candidate. It
MUST preserve predecessor ancestry, keep historical carriers immutable, and
regenerate every projection and proof whose validity depends on the new HEAD.

#### Scenario: Semantic refresh conflict fails closed

- **WHEN** the official candidate-base refresh encounters a semantic conflict
- **THEN** ETHOS MUST abort the replay and report `refresh_base_failed`
- **AND** it MUST restore the Work Lane branch and worktree to the expected clean
  head
- **AND** no manual rebase continue, skip, raw ref movement, or history
  replacement may be used to bypass the failure.

#### Scenario: Latest candidate starts a successor

- **WHEN** useful predecessor work cannot land because its candidate base is
  stale and semantic refresh failed closed
- **THEN** an owned successor MUST start from the latest observed candidate
- **AND** it MUST bind the same episode claim
- **AND** the predecessor Lane, archived Change, historical Chronicle, and proof
  receipt MUST remain observe-only.

#### Scenario: Successor preserves ancestry and regenerates evidence

- **WHEN** the successor absorbs the useful predecessor head
- **THEN** it MUST use a no-fast-forward merge with the candidate base as first
  parent and the predecessor head as second parent
- **AND** candidate-authoritative parity, configuration, and gate projections
  MUST be retained but treated as stale after the merge
- **AND** parity MUST be regenerated and proof MUST execute against the resulting
  current HEAD rather than reuse a historical receipt.

#### Scenario: Candidate advances after a topology-bearing merge

- **WHEN** candidate advances again after the continuation has created a
  topology-bearing merge but before land
- **THEN** a further owned successor MUST start from the newer candidate and
  no-fast-forward absorb the completed continuation head
- **AND** ETHOS MUST NOT linearize or discard the existing merge topology merely
  to refresh the base.

#### Scenario: Historical facts are corrected without archive mutation

- **WHEN** independent replay or review corrects a fact recorded by the
  historical carrier
- **THEN** the active continuation MUST record a superseding correction with its
  reproducible inputs and digest
- **AND** the archived Change, historical Chronicle, and historical proof
  receipt MUST NOT be rewritten.
