## Why

The terminal design (`docs/architecture/terminal-governance-product-design.md`
lines 749-800) mandates a two-package Python product — `ethos-core` (pure, IO-free
kernel) and `ethos` (product runtime) — collapsing the current eight-package
ontology. Package-level compatibility shells are unnecessary after destructive
migration (First Principle #8: compatibility residue is a cost center).

This change also closes a governance hole discovered while attempting the collapse:
a destructive, cross-boundary, architecture-level change (moving `packages/**`)
could be made with NO OpenSpec carrier and nothing blocked it (First Principle #2
violated — failure-blocking did not move upstream). This change is the carrier that
should have existed, and it is landed AFTER the admission gate that now requires it —
ETHOS governing its own largest change the same way it governs an adopter's
(single kernel, dual posture).

## What Changes

- Collapse 8 packages to 2: `ethos-contracts` + `ethos-quality` fold into
  `ethos-core` (as `ethos_core.contracts.*` / `ethos_core.quality.*`);
  `ethos-adapters` + `ethos-assistants` + `ethos-repository` + `ethos-test` fold
  into `ethos` (as `ethos.adapters.*` / `ethos.assistants.*` / `ethos.repository.*`
  / `ethos.testing.*`).
- Rewrite ~352 cross-package import sites; collapse workspace members, uv sources,
  pytest pythonpath, import-linter root_packages/contracts, ty policy tiers, and the
  path-keyed code-size ratchet exceptions to the 2-package world.
- Flip the `TARGET_PACKAGES` SSOT + `.ethos/workspace.toml` to the 2-package target
  in the final cutover commit.
- Eliminate the tracked `.agents/skills` projection (single kernel, dual posture:
  runtime reads `skills/` source; host auto-discovery comes from installing into the
  tool home, not a tracked repo projection).
- Proof: full suite + import-linter + ruff + ty + code-size green at each
  incremental package merge. Rollback: git (each package merge is one revertible
  commit). Closeout: land to candidate, retire lane.

## Capabilities

- `ethos-repository`: subject=package-ontology; reuse=modify; change=modify; facet:lifecycle=runtime; facet:surface=package; facet:authority=source

## Out Of Scope

- No behavior change to any command, gate, or governed surface — this is a
  structural relocation, not a functional change.
- Remote publication / release (Stage 8) is not part of this change.
