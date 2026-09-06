## Why

ETHOS currently describes the same active quality system through
`system/gates.toml`, `system/tools.toml`, a `runtime`/`quality` registry split,
and a Python quality projection package. The extra catalog and projections do
not own an independent invariant, so they create parallel authority and force
consumers to reconcile duplicated declarations.

## What Changes

- **BREAKING** Make `system/gates.toml` the single gate graph and remove the
  `runtime`/`quality` registry dimension.
- Delete `system/tools.toml`, its contract schema, the derived quality package,
  and the three quality projection schemas.
- Move the few surviving declarations to their existing semantic owners:
  host executables and runtime inputs to `system/surfaces.toml`, downloaded
  tool identity to native supply policy, and executable ownership to selected
  gate/provider scripts and their transitive script dependencies.
- Update consumers, fixtures, skills, documentation, and semantic-closure tests
  without compatibility loaders, aliases, or a replacement catalog.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: Keep one gate declaration and one owner per quality property.
- `repository-governance`: Admit tools and executable references only through
  current gates, native configuration, supply policy, or selected scripts.

## Impact

The change removes one TOML catalog, four schemas, one Python package, and the
registry selector from gate contracts and adopter profiles. Existing gate IDs,
proof sets, commands, and evidence semantics remain intact.
