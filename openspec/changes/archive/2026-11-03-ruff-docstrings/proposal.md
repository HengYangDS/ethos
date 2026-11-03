# Proposal

## Why

ETHOS checks docstrings twice. The managed Ruff policy selects the pydocstyle rules under the Google
convention, so every module and package needs a docstring (`D100`, `D104`) and every docstring is
checked for its summary, sections and argument descriptions (`D205`, `D415`, `D417`, `D419` and the
rest). The `docstrings` gate then runs ETHOS's own checker, `src/ethos/repository/policy/docstrings/`
(403 lines, with a 298-line test), over the same files. Beyond what Ruff checks, it adds a
documented name that the signature lacks, a docstring on every CLI command, and three heuristics:
weak summaries, reStructuredText markers and unknown section names. The approved end-state design
routes this to `ruff-docstrings` (section 11, phase 1).

## What Changes

- The managed Ruff policy selects `DOC102` (`docstring-extraneous-parameter`), a preview rule
  selected by its exact code like `PLW1514`, so a documented argument that the signature lacks still
  fails lint in ETHOS and in every governed Python repository.
- A CLI surface case requires help text, which Cyclopts takes from the command's docstring, for
  every registered command.
- Retire the `docstrings` gate: its registry row and Nox session,
  `.config/checks/docstrings/policy.toml`, the provider package and its test. The three heuristics
  retire with it; no Ruff rule covers them.
- `rules/module-layout.md`, the configuration reference and `CHANGELOG.md` name the new owners.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The quality floor still requires a docstring policy, which Ruff and the CLI surface case now
own, so `skip_specs: true` applies.

## Impact

Product code loses the 403-line provider; tests lose its 298-line test and gain one CLI surface
case. The gate registry, the Ruff policy, the Nox sessions and three documents change. Governed
Python repositories receive `DOC102` with the next release of the managed Ruff policy.
