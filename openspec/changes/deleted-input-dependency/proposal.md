# Proposal

## Why

On 2026-10-31 an adopter lane replaced its vendored copy of a library with the published
distribution: its patch deletes the 66 files of `src/filmkit/` and changes `pyproject.toml` to
depend on the locked `filmkit` release, as its Change `adopt-filmkit` requires. Prewrite blocked
the patch with 12 `deleted_input` gaps such as
`deleted_input:src/filmkit/film.py:tests/test_film.py:import`. Deletion admission maps every
surviving `import filmkit.film` to the deleted `src/filmkit/film.py`, although after the patch the
declared dependency serves that import. The adopter cannot retire its copy through ETHOS.

## What Changes

- Deletion admission no longer counts a deleted Python module as a dangling input when the root
  `pyproject.toml` declares a dependency whose normalized name equals the module's top-level
  package. Project dependencies, optional dependencies and dependency groups count.
- The project's own name never counts as a dependency, so deleting the project's own package
  with a surviving import still blocks. A dependency of another name, or an unreadable
  `pyproject.toml`, also keeps the block.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: deletion admission recognizes a declared dependency that replaces a
  deleted package.

## Impact

- `src/ethos/repository/policy/references/manifests.py` and `observation.py`, with their tests.
- A dependency whose import name differs from its distribution name, such as PyYAML's `yaml`,
  still blocks; the design records why.
