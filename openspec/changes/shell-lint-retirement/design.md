# Design

## Context

The paradigm's script rule (`repository/paradigm/scripts.py`) admits a tracked script only as the
digest-recorded output of a catalogued generator. ETHOS's own `shell-lint` therefore never has a
subject. The format policy's `validation_*`, `owner`, `execution` and `truth_boundary` fields are
descriptive: only `format_owner` and `mutation_policy` are acted on. ShellCheck elsewhere runs with
`--norc` (`ci_projection`, `code_quality`), so `.shellcheckrc` has no other reader. Three
committee rounds (scratch `gates-review/`) settled the decisions below.

## Goals / Non-Goals

Goals: no ETHOS gate passes on nothing it could judge, and no shipped row names a command that only
ETHOS has, for shell.

Non-Goals:

- retiring shfmt, a runtime dependency used by `source-format`, which needs a lock and supply move;
- the 26 other shipped rows that name ETHOS-only Nox sessions, which need their own Change;
- the gate-applicability work on empty selections.

## Decisions

1. Remove the gate, its session, the hook and `.shellcheckrc` in one Change, with every reference:
   registry, docs, Skill, activation and tests. A `git grep` for `shell_lint`, `shell-lint` and
   `shellcheckrc` closes the Change.
2. The shell `[[ownership]]` row names `repository-paradigm` as validation owner and `ethos prove
--json` as validation command. The `[[format]]` row names the paradigm declaration, the same
   command and "recorded official generator output". `format_owner` stays shfmt until its own
   retirement.
3. The removed parametrized case was the only test of the session inventory helper `_paths`, so a
   direct test keeps live paths and drops deleted ones.

## Risks / Trade-offs

- A governed repository that tracks a generator-recorded shell script keeps today's behaviour;
  only its descriptive rows change.
