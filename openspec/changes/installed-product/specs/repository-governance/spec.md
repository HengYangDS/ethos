## MODIFIED Requirements

### Requirement: Exact accepted proposal retirement

ETHOS SHALL retire a proposal through its existing publication effect only after
fresh observations establish accepted absorption, closed review, and exact
peer ref identity. Retirement SHALL NOT depend on main release convergence,
active Change presence, or a historical authoring Lease.

#### Scenario: Accepted contribution no longer needs its review projection

- **WHEN** a proposal tip is reachable from local accepted dev and the selected
  peer's accepted dev, and no matching review remains open
- **THEN** public publication can delete that exact proposal by peer-local CAS
- **AND** a delayed main release does not block retirement

#### Scenario: Incomplete or unrelated evidence cannot authorize deletion

- **WHEN** absorption is absent, a review is open, the peer tip changed, or a
  required observation is unavailable
- **THEN** retirement preserves the proposal and reports the owning boundary
- **AND** patch equivalence, a user-supplied closed flag, and unrelated review
  results cannot substitute for the required observations

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

#### Scenario: Remote retirement exposes separately admitted local closure

- **WHEN** selected peer retirement has completed but a same-named local proposal remains
- **THEN** the result preserves confirmed remote effects and reports `retirement_pending`
- **AND** its continuation invokes the native local retirement owner with exact root and OIDs
- **AND** the publication receipt does not authorize that local mutation
- **AND** replay reports full retirement only after the requested local projections are absent

#### Scenario: Local retirement shares verified accepted-contribution meaning

- **WHEN** a local proposal is accepted by ancestry, verified signature repair or conserved native refresh
- **THEN** its native retirement and compensation consume the same contribution observer as publication
- **AND** topic role, current accepted OID, no linked worktree, no Lease and exact CAS still apply
- **AND** missing, invalid or nonconserving evidence blocks deletion; unavailable conservation remains UNKNOWN
- **AND** failed local effect evidence preserves or compensates the exact original ref
