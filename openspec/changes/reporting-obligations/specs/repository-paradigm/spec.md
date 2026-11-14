## MODIFIED Requirements

### Requirement: Paradigm conformance is a blocking verdict

The repository audit SHALL report every paradigm gap with its carrier, the violated obligation and
the canonical repair. The paradigm SHALL declare the obligations that report and do not block; a
gap of such an obligation SHALL be listed apart from the required gaps and SHALL NOT change the
verdict or select the report's next action. While any other gap remains, prove, land and publish
SHALL be blocked. Prewrite admission SHALL refuse a write that would create a path the paradigm
rejects. A path that the index or HEAD tracks is not created by its write, so prewrite SHALL admit
its deletion.

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

#### Scenario: Only a reporting obligation has gaps

- **WHEN** a governed repository's only paradigm gaps belong to an obligation that the paradigm
  declares as reporting
- **THEN** the paradigm report passes, lists each gap with its repair under its reported gaps and
  names no required gap
- **AND** prove, land and publish are not blocked by them.

### Requirement: Python packages state their purpose

Every tracked `__init__.py` that a repository authors SHALL open with a docstring that names its
package's purpose; an empty marker or one without a docstring SHALL be a paradigm gap. The paradigm
report SHALL name each one. The obligation SHALL be a reporting obligation: its gaps SHALL NOT
block, and `pre-commit` SHALL admit a staged marker without a docstring.

#### Scenario: A package marker is empty

- **WHEN** a repository tracks an empty `src/app/__init__.py`
- **THEN** the paradigm reports `repository_paradigm_package_docstring:src/app/__init__.py` among
  its reported gaps and not among its required gaps.

#### Scenario: A package marker states its purpose

- **WHEN** `src/app/__init__.py` opens with `"""Application commands."""`
- **THEN** the paradigm reports no package gap.

#### Scenario: An empty marker is staged

- **WHEN** a commit stages an empty `__init__.py`
- **THEN** `pre-commit` admits it.
