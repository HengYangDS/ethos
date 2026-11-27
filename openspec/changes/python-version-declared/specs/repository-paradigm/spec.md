## MODIFIED Requirements

### Requirement: Configured formatters share one width

Every configured formatter SHALL use a line width of 100, including Prettier, Taplo and Ruff. A
repository that configures Ruff SHALL declare its own `target-version` in its Ruff carrier; where
the shipped settings and the repository's render a Python file differently, the format check SHALL
render it at the repository's target.

#### Scenario: A formatter keeps its default width

- **WHEN** a repository's Ruff configuration sets or defaults to a line length of 88
- **THEN** the paradigm reports a non-common formatter width.

#### Scenario: A repository's Ruff target decides its Python layout

- **WHEN** a repository's Ruff carrier declares `target-version = "py314"` and a file holds
  `except (ValueError, TypeError):`
- **THEN** the format check renders it as `except ValueError, TypeError:`, the form Ruff writes from
  Python 3.14 on.

### Requirement: Ecosystem modules lock their manifests

A repository that tracks `pyproject.toml` SHALL lock it with `uv.lock` and SHALL declare its Python
lower bound as one `>=` clause of `requires-python` that names a version. A repository that declares
npm dependencies SHALL lock them with `package-lock.json`, and a repository whose `go.mod` requires
modules SHALL track `go.sum`. Tool and runtime versions remain repository-owned under the version
policy.

#### Scenario: A Python manifest is unlocked

- **WHEN** a repository tracks `pyproject.toml` without `uv.lock`
- **THEN** the paradigm reports an unlocked Python module.

#### Scenario: A manifest without dependencies

- **WHEN** a repository's `package.json` declares only scripts, or its `go.mod` requires no modules
- **THEN** no lock is required for that module.

#### Scenario: A repository declares its own Python version

- **WHEN** a repository's `pyproject.toml` declares `requires-python = ">=3.14"` and its Ruff
  carrier declares `target-version = "py314"`
- **THEN** the paradigm reports no gap for either.
