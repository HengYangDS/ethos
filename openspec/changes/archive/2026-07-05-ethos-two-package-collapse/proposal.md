## Why

The terminal design mandates a two-package Python product — `ethos-core` (pure,
IO-free kernel) and `ethos` (product runtime) — collapsing the current eight-package
ontology. Package-level compatibility shells are unnecessary after destructive
migration (Parsimony: no compatibility residue). This is Phase F, the last
structural convergence, and it lands through a Work Lane with this OpenSpec carrier —
ETHOS governing its own largest change the same way it governs an adopter's.

## What Changes

- Collapse 8 packages to 2: `ethos-contracts` + `ethos-quality` fold into
  `ethos-core` (as `ethos_core.contracts.*` / `ethos_core.quality.*`);
  `ethos-adapters` + `ethos-assistants` + `ethos-repository` + `ethos-test` fold into
  `ethos` (as `ethos.adapters.*` / `ethos.assistants.*` / `ethos.repository.*` /
  `ethos.testing.*`).
- Rewrite the cross-package import prefixes; collapse workspace members, uv sources,
  pytest pythonpath, import-linter root_packages/contracts, ty policy tiers, and the
  path-keyed code-size ratchet exceptions to the 2-package world.
- Flip the `TARGET_PACKAGES` SSOT + `.ethos/workspace.toml` to the 2-package target
  in the final cutover commit.
- Proof: full suite + import-linter + ruff + ty + code-size green at each incremental
  package merge. Rollback: git (each merge is one revertible commit). Closeout: land
  to candidate, retire lane.

## Capabilities

- `ethos-repository`: subject=package-ontology; reuse=modify; change=modify; facet:lifecycle=runtime; facet:surface=package; facet:authority=source

## Out Of Scope

- No behavior change to any command, gate, or governed surface — a structural
  relocation, not a functional change.
- Remote publication / release (Stage 8) is not part of this change.
