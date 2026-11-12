# Design

## Context

See the [proposal](proposal.md). The paradigm report already reads tracked Python for its module
and code-size rules, and leaves received paths out of the code-size rule.

## Goals / Non-Goals

Goals:

- One rule for package markers in every governed repository, independent of its Ruff selection.

Non-Goals:

- Writing the docstrings: their text is the package's purpose, which only its authors know, so the
  gap is report-only.
- Module or function docstrings, which each repository's linter owns.

## Decisions

1. A docstring, not an empty file: a one-line statement of the package's purpose tells an agent
   what the package owns before it reads the code, and ETHOS already follows the rule everywhere.
2. `repository/paradigm/packages.py` reads each tracked, non-received `__init__.py` and reports a
   gap unless `ast.get_docstring` finds a docstring; an empty or unparsable file has none.
3. `pre-commit` applies the same function to each staged marker's index blob and refuses
   `pre_commit_package_docstring:<path>`.

## Risks / Trade-offs

- di-effect and alphasim gain hundreds of gaps at their next bind; their owners add the docstrings
  in Work Lanes before binding.
