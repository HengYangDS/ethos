## MODIFIED Requirements

### Requirement: Paradigm conformance is a blocking verdict

The repository audit SHALL report every paradigm gap with its carrier, the violated obligation and the canonical repair. While any gap remains, prove, land and publish SHALL be blocked. Prewrite admission SHALL refuse a write that would create a path the paradigm rejects. A path that the index or HEAD tracks is not created by its write, so prewrite SHALL admit its deletion.

#### Scenario: A repository conforms

- **WHEN** a governed repository has no paradigm gap
- **THEN** the audit reports a passing paradigm report and does not block.

#### Scenario: A non-conforming path is requested

- **WHEN** a Work Lane requests prewrite admission for a new root `pytest.ini`
- **THEN** admission refuses the path and names `.config/checks/pytest/pytest.toml`.

#### Scenario: A tracked non-conforming carrier is retired

- **WHEN** a Work Lane requests prewrite admission for a tracked root `pytest.ini` that it has
  deleted from the worktree, staged or not
- **THEN** admission reports no paradigm gap for the path.
