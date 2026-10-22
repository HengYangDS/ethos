## ADDED Requirements

### Requirement: Publication peer names default from their declaration

The peer ID and Git remote name SHALL be independently configurable. Within an explicit peer
declaration only, an omitted ID SHALL default to the declared provider and an omitted Git remote
SHALL default to the resolved ID. Defaults SHALL NOT create undeclared peers, infer a provider or
rename existing remotes. Explicit empty or invalid names and duplicate resolved identities SHALL
fail closed before observation or mutation.

#### Scenario: Selected providers use conventional configurable defaults

- **WHEN** GitLab or GitHub is explicitly declared without an ID or Git remote name
- **THEN** the resolved names SHALL be `gitlab` or `github` respectively
- **AND** an explicit ID or remote SHALL replace only its corresponding default
- **AND** no `origin` remote or undeclared provider SHALL be introduced

#### Scenario: Several independently named instances share one provider

- **WHEN** peers `gitlab_a`, `gitlab_b` and `github` are explicitly declared
- **THEN** both GitLab peers SHALL use the GitLab adapter without sharing identity
- **AND** publication SHALL support selecting any declared subset independently

## MODIFIED Requirements

### Requirement: Exact accepted proposal retirement

ETHOS SHALL retire a proposal through its existing publication effect only after
fresh observations establish closed review, exact peer ref identity, and that its
exact tip stays preserved: by accepted absorption, by an owned Work Lane that
reaches it, or by the same peer's ref for its closed review. A candidate ref
SHALL NOT retain a proposal. Retirement SHALL NOT depend on main release
convergence, active Change presence, or a historical authoring Lease.

#### Scenario: Accepted contribution no longer needs its review projection

- **WHEN** a proposal tip is reachable from local accepted dev and the selected
  peer's accepted dev, and no matching review remains open
- **THEN** public publication can delete that exact proposal by peer-local CAS
- **AND** a delayed main release does not block retirement

#### Scenario: A retained projection is redundant

- **WHEN** an unabsorbed proposal tip is reachable from an owned Work Lane, or
  the same peer names it at the ref of a closed review of that branch, and no
  matching review remains open
- **THEN** public publication can delete that exact proposal by peer-local CAS
- **AND** the report names the retainer that keeps the tip retrievable

#### Scenario: Incomplete or unrelated evidence cannot authorize deletion

- **WHEN** neither absorption nor a retainer is observed, a review is open, the
  peer tip changed, or a required observation is unavailable
- **THEN** retirement preserves the proposal and reports the owning boundary
- **AND** patch equivalence, a user-supplied closed flag, unrelated review
  results, and a candidate ref that landing resets cannot substitute for the
  required observations

#### Scenario: Replayed deletion converges without repeated effects

- **WHEN** one peer was retired before interruption and another remains pending
- **THEN** recovery reobserves the same exact plan and skips the absent peer
- **AND** remaining peers are independently readmitted before deletion

#### Scenario: Verified history repair preserves accepted contribution identity

- **WHEN** an immutable, completed ETHOS history-repair effect establishes one
  exact old proposal tip to replacement mapping, and the replacement is absorbed
  by local and peer accepted dev
- **THEN** retirement recognizes that verified relationship without restoring
  the old history
- **AND** missing, ambiguous or invalid repair evidence cannot authorize deletion

#### Scenario: Publication retains its original positive-object guarantees

- **WHEN** the existing publication command projects commits or annotated tags
- **THEN** target updates still match the exact trusted source object
- **AND** retirement mode cannot delete protected, candidate, or tag resources

#### Scenario: Verified native refresh preserves the accepted contribution

- **GIVEN** validated native refresh evidence binds the old contribution, candidate
  and refreshed output, and the proposal is contained in the old input history
- **WHEN** isolated native composition reproduces the exact output tree and the
  output is absorbed by local and peer accepted dev
- **THEN** public retirement consumes that relationship without recreating an
  active historical Change, Lease or old branch
- **AND** current closed-review, exact peer identity and fresh CAS checks still apply
- **AND** missing, invalid, ambiguous or nonconserving evidence does not authorize
  deletion, while unavailable required observations remain explicit
