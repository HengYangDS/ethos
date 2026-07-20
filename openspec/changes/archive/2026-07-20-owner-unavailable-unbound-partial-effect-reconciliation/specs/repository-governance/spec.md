## MODIFIED Requirements

### Requirement: Ref-absent owner-unavailable partial effects are reconciled only through exact native lease CAS

When a prior native exceptional-retirement attempt is immutable evidence but
the target ref is absent and its exact foreign lease remains, ETHOS SHALL expose
`ethos lane retire reconcile-ref-absent` as a distinct native reconciliation.
It SHALL require a current accepted Chronicle and Claim whose bytes match the
accepted branch, an exact source lease tuple and absent source-path binding, a
non-empty recovery actor different from the source holder, and a Chronicle
binding to the immutable prior attempt’s operation ID, accepted head, Claim,
Chronicle ref, and digests. Apply SHALL require authorization, break-glass, and
irreversible confirmation. It SHALL neither recreate nor delete a source ref.

#### Scenario: Exact ref-absent residue is reconciled

- **WHEN** the ref and source worktree are absent, protected refs and current
  accepted policy remain stable, and the current lease exactly matches the
  accepted Chronicle and immutable source attempt
- **THEN** ETHOS SHALL revoke only that exact source lease generation through a
  native CAS
- **AND** it SHALL report `reconciled_ref_absent_owner_unavailable_lease` only
  after postconditions prove ref, worktree, and lease absence plus unchanged
  protected refs and Chronicle binding.

#### Scenario: Reconciliation observation or evidence drifts

- **WHEN** a source ref or worktree reappears, or the lease tuple, source path,
  current Chronicle/Claim bytes, source attempt, accepted control root, or
  protected refs drifts
- **THEN** ETHOS SHALL block before lease mutation
- **AND** it SHALL preserve the foreign lease and all refs unchanged.
