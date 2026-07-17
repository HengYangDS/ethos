# Tool Adoption Catalog SSOT

## Why

`system/tools.toml` records tool concerns, profiles, gates, and configuration,
but quality reporting also maintains a static Python adapter table. The two
surfaces can drift: a catalog entry may be planned, active, or adapter-only
without the command projection exposing the same adoption fact.

## What Changes

- Make every catalog entry declare an adoption state: `active`, `candidate`,
  `deferred`, or `rejected`.
- Require that state, profile, and configuration in the tools contract schema.
- Derive `ethos quality tool-profiles` and the quality-profile schema instance
  from the tracked catalog rather than from a parallel static Python table.
- Preserve catalog optional fields in the command payload so a consumer can
  distinguish a current gate from an adapter-only or deferred mechanism.
- Add regressions for exact catalog projection and adoption-state validation.

## Capabilities

- `quality`: subject=tool-adoption-catalog-ssot; reuse=extend; change=modify;
  facet:lifecycle=declaration,validation,projection; facet:surface=system,
  schema,command,test,openspec; facet:authority=system/tools.toml,
  schema,source,test

## Out Of Scope

- No tool is installed, upgraded, invoked, or removed by this change.
- No candidate, deferred, or rejected entry becomes an active gate merely by
  appearing in the catalog.
- No provider, remote, release, tag, or branch is mutated.
