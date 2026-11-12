## ADDED Requirements

### Requirement: Python packages state their purpose

Every tracked `__init__.py` that a repository authors SHALL open with a docstring that names its
package's purpose; an empty marker or one without a docstring SHALL be a paradigm gap. The paradigm
report SHALL name each one, and `pre-commit` SHALL refuse a staged one.

#### Scenario: A package marker is empty

- **WHEN** a repository tracks an empty `src/app/__init__.py`
- **THEN** the paradigm reports `repository_paradigm_package_docstring:src/app/__init__.py`.

#### Scenario: A package marker states its purpose

- **WHEN** `src/app/__init__.py` opens with `"""Application commands."""`
- **THEN** the paradigm reports no package gap.

#### Scenario: An empty marker is staged

- **WHEN** a commit stages an empty `__init__.py`
- **THEN** `pre-commit` refuses with `pre_commit_package_docstring` and the file's path.
