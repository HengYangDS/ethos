---
subject: ethos:invalid-state-release-resource
reuse: extend
change: modify
facet:lifecycle: release
facet:surface: package-runtime
facet:authority: contracts
---

# Invalid-State Release Resource

## Why

The invalid-state taxonomy is repository truth under `system/invalid_states.toml`,
but installed `ethos-core` wheels run outside the source checkout. A packaged
runtime that cannot read the taxonomy weakens the substrate and makes the
kernel-derived failure vocabulary unavailable exactly when ETHOS is used as a
product dependency.

## What Changes

- Keep `system/invalid_states.toml` as the SSOT in source checkouts.
- Add a parsed-equivalent release mirror at `ethos_core/data/invalid_states.toml`.
- Load the source SSOT when present, otherwise load the packaged resource.
- Add tests proving the mirror matches the SSOT and works outside a checkout.

## Out Of Scope

- No new invalid-state category.
- No second truth store: the packaged resource is a release mirror checked
  against the source contract.
- No command-plane change.
