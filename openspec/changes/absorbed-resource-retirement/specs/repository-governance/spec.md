## ADDED Requirements

### Requirement: Absorbed local resource retirement is independent of authoring role

ETHOS SHALL admit deletion-only retirement of an explicitly selected local topic
ref whose exact HEAD is equal to or an ancestor of current accepted truth,
without requiring the ref to use the Work Lane authoring prefix. Accepted,
release, and candidate resources SHALL remain outside this retirement path.
The existing retirement protocol SHALL retain actor, Lease, cleanliness,
exact-CAS, post-observation, and recovery obligations. This capability SHALL NOT
grant source-write authority or retire remote review projections.

#### Scenario: An absorbed unlinked topic ref predates current policy

- **WHEN** an authorized caller selects an exact unlinked, unleased topic ref
  absorbed by the exact current accepted HEAD
- **THEN** the public absorbed-ref retirement and installed reference-transaction
  hook admit the same exact deletion under current accepted policy
- **AND** the old object need not contain the current repository policy schema
- **AND** the command attests ref absence without changing repository roots.

#### Scenario: A clean linked topic worktree is already absorbed

- **WHEN** an authorized caller selects an exact clean linked topic worktree
  absorbed by accepted truth with no valid foreign Lease
- **THEN** public landed retirement removes only that worktree and ref through
  the existing observed retirement operation
- **AND** it preserves exact-generation Lease handling and resumable failures.

#### Scenario: Eligibility does not grant arbitrary deletion

- **WHEN** the target is a repository root, dirty, not absorbed, held by a valid
  foreign Lease, or differs from the admitted exact coordinates
- **THEN** retirement blocks before destructive effects and preserves the target
- **AND** a bare ref deletion without prepared retirement intent cannot use this
  public retirement authority.
