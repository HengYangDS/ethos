# Design

## Context

See the [proposal](proposal.md). ETHOS's Git adapter strips every ambient `GIT_` variable except
the identity ones (`src/ethos/adapters/repo/git.py:199-201`), so `GIT_CEILING_DIRECTORIES` set by a
test session would not reach product calls. Refusing a base temporary directory inside a work tree
needs no product change.

## Goals / Non-Goals

Goals: no test session runs with its temporary root inside a repository.

Non-Goals: changing product discovery, and guarding tests that pass an explicit repository root.

## Decisions

1. `work_tree_refusal(basetemp) -> str | None` lives beside `GIT_ISOLATION` in
   `tests/support/git_isolation.py`. It asks Git, with every `GIT_` variable removed, whether
   the directory is inside a work tree or a Git directory (`rev-parse --is-inside-work-tree`
   and `--is-inside-git-dir`), and returns a refusal when either answer is `true`.
2. A session-scoped autouse fixture in `tests/conftest.py` calls it with pytest's base temporary
   directory and calls `pytest.exit` with the refusal, so no test starts. With xdist, each worker
   checks its own base directory, which sits under the controller's.
3. The default base directory is in the system temporary directory, so ordinary runs are
   unchanged.

## Risks / Trade-offs

One `git rev-parse` per worker session: negligible.
