## Context

Official OpenSpec boundary: `ethos-repository` capability `package-ontology`.
ETHOS repo-local product boundary: the workspace package topology (`packages/**`,
`pyproject.toml` workspace/sources, `.config/checks/*`, `.ethos/rules.toml`
code-size, and the `TARGET_PACKAGES` SSOT in `ethos_contracts.package_ontology`).

## Design

Incremental, one package at a time — NOT big-bang. Each package merge is a single
revertible commit that ends green (pytest + import-linter + ruff + ty + code-size).

Mapping (per terminal design lines 749-800):
- `ethos-core` absorbs the pure leaves: `ethos-contracts` -> `ethos_core.contracts.*`,
  `ethos-quality` -> `ethos_core.quality.*`. Verified IO-free (only tomllib+Path,
  same shape as the existing pure `ethos_core.measure`).
- `ethos` absorbs the product runtime: `ethos-adapters` -> `ethos.adapters.*`
  (alongside existing ethos/adapters/{git,config,quality_tool}), `ethos-assistants`
  -> `ethos.assistants.*`, `ethos-repository` -> `ethos.repository.*`, `ethos-test`
  -> `ethos.testing.*`.

Ownership: `ethos-core` owns kernel semantics; `ethos` owns runtime. Routing: import
prefixes rewritten (~352 sites). Promotion targets: workspace config + import-linter
+ ty + code-size + TARGET_PACKAGES SSOT + `.ethos/workspace.toml`.

Lockstep hazards (from the collapse plan): (a) the code-size ratchet is PATH-keyed —
each moved monolith's exception path must be repathed in the SAME commit that moves
it (effective-LOC is move-invariant, so no shrink needed, only re-anchoring);
(b) `test_product_boundaries` forbids `tomllib` in ethos-core — lift that before the
contracts move; (c) the `TARGET_PACKAGES` SSOT + `.ethos/workspace.toml` flip is
deferred to the final cutover commit so SSOT-asserting tests don't fail mid-migration.

Also folds in the `.agents/skills` projection elimination (single kernel, dual
posture): runtime registry reads `skills/` source; `.agents/skills` tracked tree is
removed; host auto-discovery is install-to-tool-home, not a tracked projection —
identical for self and adopter.

## Alternatives

Big-bang collapse rejected: rewriting ~352 imports + 12 code-size paths + 2
import-linter contracts + ty + workspace + ontology SSOT simultaneously makes the
first red gate impossible to localize. Incremental gives a green checkpoint per
package.

## Proof Strategy

Static: ruff, import-linter (`--no-cache`), ty per-package policy, code-size gate,
lychee. Executed proof: `ethos prove --execute --expect-head <head>`. OpenSpec:
`openspec validate --all --strict`. Full `pytest` green (5 pre-existing
parity-treadmill failures excepted) at each package-merge checkpoint. Evidence:
per-commit gate output on lane `work/surface-split`.
