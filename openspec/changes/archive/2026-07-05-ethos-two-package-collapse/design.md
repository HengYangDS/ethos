## Context

Official OpenSpec boundary: `ethos-repository` capability `package-ontology`.
ETHOS repo-local product boundary: the workspace package topology (`packages/**`,
`pyproject.toml` workspace/sources, `.config/checks/*`, `.ethos/rules.toml`
code-size, and the `TARGET_PACKAGES` SSOT in `ethos_contracts.package_ontology`).

## Design

Incremental, one package at a time — NOT big-bang. Each package merge is a single
revertible commit that ends green (pytest + import-linter + ruff + ty + code-size).

Mapping (terminal design lines 749-800):
- `ethos-core` absorbs the pure leaves: `ethos-contracts` -> `ethos_core.contracts.*`,
  `ethos-quality` -> `ethos_core.quality.*`. Both are IO-free (only tomllib+Path).
- `ethos` absorbs the product runtime: `ethos-adapters` -> `ethos.adapters.*`
  (alongside existing ethos/adapters/), `ethos-assistants` -> `ethos.assistants.*`,
  `ethos-repository` -> `ethos.repository.*`, `ethos-test` -> `ethos.testing.*`.

Lockstep hazards: (a) the code-size ratchet is PATH-keyed — each moved monolith's
exception path repathed in the SAME commit that moves it (effective-LOC is
move-invariant); (b) `test_product_boundaries` forbids `tomllib` in ethos-core — lift
that with the contracts move; (c) the `TARGET_PACKAGES` SSOT + `.ethos/workspace.toml`
flip is deferred to the final cutover commit so SSOT-asserting tests don't fail
mid-migration.

## Alternatives

Big-bang collapse rejected: rewriting all import sites + code-size paths + import-
linter contracts + ty + workspace + ontology SSOT simultaneously makes the first red
gate impossible to localize. Incremental gives a green checkpoint per package.

## Proof Strategy

Static: ruff, import-linter (--no-cache), ty per-package policy, code-size gate,
lychee. Executed proof: `ethos prove --execute --expect-head <head>`. OpenSpec:
`openspec validate --all --strict`. Full `pytest` green (5 pre-existing excepted) at
each package-merge checkpoint. Evidence: per-commit gate output on the lane.
