# Design

## Context

See [proposal.md](proposal.md). The `docstrings` gate's provider reports two things. Coverage
counts each package `__init__.py` and each function decorated as a CLI command; Ruff's `D104`
already requires the first. Style checks every existing docstring for an empty summary, a summary
ending in a colon, a weak summary, reStructuredText markers, unknown section names, and an `Args`
section that misses or adds a name. `D419`, `D415` and `D417` already cover three of these. The
managed policy lives in `.config/checks/ruff/ruff.toml`, which the wheel ships and the native
gates apply as the mandatory floor of every governed repository
(`src/ethos/adapters/gates/native/inputs.py:221-229`).

## Goals / Non-Goals

**Goals:**

- Ruff and the CLI surface tests own every docstring obligation that the gate enforced, except the
  three heuristics.
- ETHOS no longer ships or runs its own docstring checker.

**Non-Goals:**

- Requiring docstrings on public classes, methods or other functions; `D101` to `D107` other than
  `D104` stay ignored.
- Other repositories' CLI surfaces.

## Decisions

- **`DOC102` in the managed floor.** It replaces the gate's extra-argument check and is generic, so
  it belongs with `D417` in the shared policy. On this head it reports no finding over `src`,
  `tests` and `tools`.
- **Command help in a CLI surface case, not `D103`.** Ruff cannot select only decorated functions,
  and a per-file `D103` would put ETHOS's package paths into a policy that every governed repository
  receives. The case walks the registered Cyclopts commands and requires each one's help text,
  which is what a user sees; 47 commands carry it today.
- **Drop the three heuristics.** No Ruff rule implements them, and keeping them would keep ETHOS's
  checker for about 45 lines of guesswork.

## Risks / Trade-offs

- [A governed repository documents an argument its signature lacks] → Its next ETHOS bump reports
  `DOC102`; the release notes name the rule.
- [A summary such as "Helper." passes again] → Review owns wording; `D415` still requires a sentence.
