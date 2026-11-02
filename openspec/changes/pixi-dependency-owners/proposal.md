# Proposal

## Why

Patch admission refuses a reference that no baseline declaration owns. A Mise tool owns the
executable it names ("A toolchain declaration owns the executable it names"), but a Pixi manifest
owns nothing: ETHOS reads Pixi environments only to map installed Python distributions to modules.
di-effect declares `pip = "*"` in `pixi.toml` (`[feature.host.dependencies]`), the host environment
its onboarding guide makes authoritative, and still every edit of that guide is refused with
`product_reference_not_admitted_at_baseline:executable:pip`, because the guide's existing
`pip install` examples are observed in the touched file (Codex handoff a225, 2026-11-02).

## What Changes

- A conda dependency that a Pixi manifest declares owns the executable of its package name on every
  platform, installed or not, as a Mise tool owns its own. The manifest is `pixi.toml`, or the
  `[tool.pixi]` tables of `pyproject.toml` when no `pixi.toml` exists. Every conda dependency table
  counts: `[dependencies]`, `[target.*.dependencies]`, `[feature.*.dependencies]` and
  `[feature.*.target.*.dependencies]`.
- A package's other executables (`pip3`, for example), PyPI dependencies, `[constraints]` and
  `[workspace.dependencies]` own nothing.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: a Pixi conda dependency owns the executable it names.

## Impact

`src/ethos/repository/policy/references/` (the Pixi manifest becomes a declaration carrier) and its
tests. No adopter declaration changes; di-effect's existing `pip` declaration starts to own `pip`.
