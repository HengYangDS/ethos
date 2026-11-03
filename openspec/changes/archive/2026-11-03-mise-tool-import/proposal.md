# Proposal

## Why

`release-journey` moved the Mise installation of a declared ETHOS tool into
`tools/ci/delivery/mise_tool.py`, and `tools/ci/delivery/distribution.py` imported that module's
`run` function under the name `run_mise`. The module-layout policy admits a public `from` import
under another name only for a module namespace or a name the importing module binds, so the
`module-layout` gate reported `module_layout_import_rename` and the full proof of the archived head
stopped at that readiness gate.

## What Changes

- `tools/ci/delivery/distribution.py` imports the `mise_tool` module and calls `mise_tool.run`; it
  keeps importing `CONSOLE_DIRECTORY` and `install_declared` by their own names.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The module-layout requirement already governs this import, so `skip_specs: true` applies.

## Impact

One import and one call in `tools/ci/delivery/distribution.py`. No behavior, document or release
entry changes.
