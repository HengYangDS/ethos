# Design

## Context

Exact patch admission evaluates deleted paths against the surviving files of the effective
postimage (`adapters/admission/patch_admission.py`, `_effect_gaps`).
`repository/policy/references/observation.py` `deleted_input_gaps` joins the deletions to
surviving native consumers; for Python, `python_syntax.deleted_python_input_gaps` maps each deleted
`.py` path to its module name and reports every surviving import of that module. The mapping
treats the repository's own tree as the only source of a module. A module that a declared
dependency installs is outside that view.

The adopter's prewrite record of 2026-10-31 shows the effect: one patch deleted the 66 files
under `src/filmkit/` and changed `pyproject.toml` to depend on the published `filmkit` release; 12
imports in its tests were reported as dangling.

## Goals / Non-Goals

**Goals:**

- A patch that replaces a vendored package with a declared dependency of the same name is
  admitted.
- Deleting the project's own package, or a package no declaration provides, still blocks.

**Non-Goals:**

- Resolving installed distribution metadata, `top_level.txt` or import-name aliases.
- Nested Python projects below the repository root.

## Decisions

### 1. Name equality is the evidence

Admission runs before installation and offline, so it cannot ask an installed distribution which
packages it provides. It compares the top-level package of the deleted module with each declared
requirement's name, both normalized by the PEP 503 rule ETHOS already uses for declared
distributions. Equal names are the common case of a vendored copy; a distribution whose import
name differs, such as PyYAML's `yaml`, stays blocked. A false block names the deleted input and
its consumer; a false pass would remove an input the repository still needs.

### 2. Which declarations count

The root `pyproject.toml` declares the dependencies the repository's code and tests run with:
`[project].dependencies`, `[project.optional-dependencies]` and `[dependency-groups]`. Build-system
requirements do not run with the code and do not count. The project's own `[project].name` never
counts, because its package is the repository's own source. The declarations are read from the
effective postimage, so a patch that adds the dependency and deletes the copy is judged as one
change.

### 3. Where the rule lives

`PythonManifest` in `manifests.py` already owns the consumed `pyproject.toml` fields and their
normalization; it gains the list of dependency distributions. `deleted_input_gaps` removes the
deletions those distributions provide before it asks for Python import gaps. Other native inputs,
such as `package.json` scripts, still see every deleted path.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| A declared dependency does not actually provide the package | The proof installs the declared dependencies and runs the surviving imports. |
| A repository declares a dependency named like its own package | The project's own name is excluded; a different distribution of the same name is the repository's declared choice. |
