## ADDED Requirements

### Requirement: A new obligation enters as reporting

An obligation that a release ships for the first time SHALL be declared as reporting in that
release, and SHALL leave the declaration only in a later release that ships its repair. An
obligation shipped through 0.2.0-beta.10 and absent from the declaration is armed. The semantic
closure, which the audit reports beside its verdict, is the one other finding that does not
block, and it keeps its own carrier until rules have rows.

#### Scenario: A release ships an obligation for the first time

- **WHEN** a release adds an obligation that no earlier release reported
- **THEN** the paradigm declares it as reporting, and its gaps appear among the reported gaps.

#### Scenario: An obligation shipped earlier is absent from the declaration

- **WHEN** an obligation shipped through 0.2.0-beta.10 is not declared as reporting
- **THEN** its gaps are required and block.

## MODIFIED Requirements

### Requirement: Paradigm conformance is a blocking verdict

The repository audit SHALL report every paradigm gap with its carrier, obligation and repair. The
paradigm SHALL declare the obligations that report and do not block; their gaps SHALL be listed
apart from the required gaps and SHALL NOT change the verdict or the next action. While any other
gap remains, prove, land and publish SHALL be blocked. Prewrite admission SHALL refuse a write that
would create a path the paradigm rejects, and SHALL admit the deletion of a tracked one.

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
