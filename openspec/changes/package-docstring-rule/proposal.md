# Proposal

## Why

On 2026-11-12 the owner asked for one rule for `__init__.py`: a docstring or an empty file. The
governed repositories disagree, measured that day:

- ETHOS opens all 97 of its package markers with a one-line docstring, and its Ruff selection
  enforces it (pydocstyle D104).
- openai-responses-proxy and filmkit do the same: 27 of 27 and 7 of 7.
- web-ingestion-benchmark mixes them, 6 empty and 2 with a docstring, and alphasim has 202 empty and
  346 with one.
- di-effect has 1,468, all empty.

The paradigm states no rule, so each repository's own Ruff selection decides.

## What Changes

- Every tracked `__init__.py` opens with a docstring that names the package's purpose; an empty or
  docstring-less marker is a paradigm gap, `repository_paradigm_package_docstring:<path>`.
- `pre-commit` refuses a staged marker without a docstring.
- The Unreleased section of `CHANGELOG.md` gains a Breaking line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: ADDED `Python packages state their purpose`.

## Impact

A new module in `src/ethos/repository/paradigm/`, the paradigm report, the pre-commit hook, their
tests and `CHANGELOG.md`. ETHOS has no gap; governed repositories with empty markers do.
