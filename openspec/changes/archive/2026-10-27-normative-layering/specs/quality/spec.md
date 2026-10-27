## ADDED Requirements

### Requirement: Isolated Python static analysis judges the declared target

The product's Python static provider SHALL keep its isolated common rules,
which repository ignores cannot narrow, and SHALL judge authored Python at the
repository's declared version: its accepted Ruff `target-version`, following
`extend` inside the repository, otherwise the `requires-python` lower bound. A
missing, malformed or conflicting declaration, or a nested one giving checked
code another target, SHALL be a gap; neither the checker default nor ETHOS's
interpreter decides it.

#### Scenario: No target is declared

- **GIVEN** a repository's accepted Ruff configuration declares no
  `target-version` and its `pyproject.toml` declares no `requires-python` lower
  bound
- **WHEN** the isolated static check runs
- **THEN** it reports `python_target_undeclared` before running Ruff
- **AND** no file is judged at the checker's default target.
