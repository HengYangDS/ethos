## Why

ETHOS has a clean governance kernel, but the cross-repository comparison with
reference adopter and alternate mechanism corpus exposed concrete mechanism gaps: GitHub/GitLab parity,
provider-local CI emulation, CI template consistency, actionlint, C4/LikeC4
architecture projection, richer format/lint/security gates, evidence operations,
runbook registry, MCP smoke, and release supply-chain gates.

The gaps should be admitted as an ETHOS roadmap without promoting adopter tools
such as Nox, Pixi, Pants, Backlog, Superpowers, or `alternate mechanism corpus policy run` into
product ontology.

## What Changes

- Add a forge provider contract that makes GitHub and GitLab symmetric hosted
  projections over the same ETHOS governance contract.
- Add a tooling adoption roadmap that sequences P0/P1/P2 work packages.
- Record official-compatible OpenSpec customization rules for ETHOS schema and
  capability profile validation.
- Record Superpowers as optional replaceable method-pack adapter, not a product
  dependency.
- Extend `system/tools.toml` with planned provider, emulator, architecture,
  quality, evidence, runbook, MCP, and release adapter tools.

## Capabilities

- `repository-governance`: subject=tooling-adoption-roadmap; reuse=extend; change=modify; facet:lifecycle=planning,validation,release; facet:surface=docs,openspec,evidence,ci,schema,mcp,package; facet:authority=docs,openspec,claim,evidence,system

## Out Of Scope

- No implementation of provider templates, emulators, C4 generation, actionlint,
  SBOM, signing, or MCP smoke in this change.
- No new mandatory runtime dependency on Nox, Pixi, Pants, Backlog, Superpowers,
  GitHub, GitLab, Dagger, or `alternate mechanism corpus policy run`.
- No hosted CI success or remote publication claim.
