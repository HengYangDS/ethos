# Declarative Registry Compression Recovery

## Why

Coupling and standards registries encode durable facts as duplicated hand-written
Python dictionaries. This recovered T3/T5 slice keeps the same public payloads
while moving those facts to validated TOML and deleting the procedural builders.

## What Changes

- Compile coupling and standards registries from strict frozen Pydantic contracts.
- Keep runtime branch-role, release-profile, and toolchain facts as adapter overlays.
- Delete the static coupling and standards dictionaries.
- Use declaration-projection matrices instead of enumerative registry assertions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contracts`: subject=declarative-registry-compression; reuse=extend;
  change=modify; facet:lifecycle=authoring,validation,runtime;
  facet:surface=system,package,test,openspec;
  facet:authority=source,test,schema,docs

## Out Of Scope

No public command, coupling taxonomy, standards policy, framework runtime, or
terminal source-budget completion claim changes in this carrier.
