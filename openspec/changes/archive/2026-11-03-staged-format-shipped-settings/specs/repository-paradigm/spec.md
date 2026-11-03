## MODIFIED Requirements

### Requirement: Staged admission reads canonical configuration

When a repository configures secret scanning or Ruff, native pre-commit admission SHALL use the
configuration at its canonical `.config/` path. Configuration found anywhere else SHALL be reported
as a gap and SHALL NOT silently disable the check. When a repository configures no Ruff,
pre-commit admission SHALL check staged Python with the shipped Ruff settings.

#### Scenario: Secret scanning configuration moves

- **WHEN** Gitleaks configuration exists only at `.config/checks/gitleaks/gitleaks.toml`
- **THEN** pre-commit admission scans the staged content with that configuration.

#### Scenario: A repository keeps no Ruff configuration

- **WHEN** a repository tracks no Ruff configuration and stages a Python file that the shipped Ruff
  settings would reformat
- **THEN** pre-commit admission refuses the commit with `pre_commit_python_format_failed` for that
  path.
