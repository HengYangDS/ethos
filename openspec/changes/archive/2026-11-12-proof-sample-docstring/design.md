# Design

## Context

See the [proposal](proposal.md). The package-docstring rule makes a tracked `__init__.py` without a
docstring a required paradigm gap, and `prove` evaluates the paradigm before it runs gates.

## Goals / Non-Goals

Goals:

- The test reaches the gates it is about under the rule.

Non-Goals:

- Changing the rule, or the other tests that write `src/sample/__init__.py`: they judge gates
  directly and pass.

## Decisions

1. The sample source starts with `"""Sample package."""`. The passing variant follows it with two
   blank lines and the function; the failing variant follows it with one blank line and
   `import math`, as before. Ruff's format check accepts both, and its isolated floor reports only
   the unused import in the failing variant.

## Risks / Trade-offs

- None: the docstring adds no import or name, so the static gate fails and passes as before.
