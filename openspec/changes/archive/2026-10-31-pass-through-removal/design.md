# Design

## Context

See [proposal.md](proposal.md). The inventory measured each removal by simulating the edit and
formatting it with the locked Ruff; Ruff 0.17.3, ty and import-linter have no rule for a renaming
alias or for an import through a module that does not define the name, so the existing module-layout
owner, which already parses every governed Python file, carries both checks.

## Goals / Non-Goals

**Goals:**

- No pass-through, assignment alias, renaming alias or indirect import that the inventory marks
  removable remains in `src/ethos`, `tools` or the tests.
- A new renaming alias or indirect import fails module-layout at proof.

**Non-Goals:**

- Constant-binding wrappers that name a distinct query, policy or scope; registered adapters such as
  CLI commands, gate providers named in TOML, pydantic validators and pytest hooks.
- Namespace aliases (`import a.b as c`), which `rules/module-layout.md` 2.5.1 permits.
- The CI provider emulation, which a later Change retires whole.

## Decisions

- **The owner takes the better name.** When several importers rename one generic owner the same way,
  the owner is renamed and the aliases go; the name that importers chose states the concept.
- **One alias exception.** A renaming alias stays legal only when another binding or definition in
  the importing module already holds the original name, or when the imported name is a module; then
  the alias disambiguates rather than renames.
- **The definer is resolved from the repository's own modules.** An import from a governed module
  that binds the name by importing it is reported with the defining module; third-party modules are
  outside the check.
- **`proof_artifact_root` goes.** Its docstring promised a root holding only proof artifacts, but it
  returns the general state root, and no planned separate root exists in the end-state design.

## Risks / Trade-offs

- [A test patches a removed name] → Each patch moves to the owner the consumer imports; the
  inventory lists every patched site.
- [The checks report a legitimate case] → The exception covers collisions and module namespaces; the
  full proof runs the checks over every governed file before landing.
