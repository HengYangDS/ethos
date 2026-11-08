# Proposal

## Why

The root catalog (`2026-11-08-catalog-root`) declares 29 operations, but each SDK function still
picks its body by first match after the catalog's selection, so the two can drift apart without a
test failing, and fifteen import-linter rows keep the console, the result bound and the runtime
identity reachable from the surface. Each operation should run exactly one implementation, chosen
once, and the console should live in the application layer.

## What Changes

- `ethos.application.catalog.IMPLEMENTATIONS` maps each of the 29 operation IDs to one
  `(root, request)` implementation; `invoke` selects and runs it, and each SDK function only returns
  `invoke("<command>", root, locals())`, keeping its name, keyword signature, defaults and
  docstring. `catalog_operation` goes.
- Land and publish keep their preambles in private `_landing` and `_publishing` decorators; prove's
  readiness and host observations become their own implementations; status and plan bodies move
  unchanged.
- Changed: the root SDK functions run the request their selection validated, as the CLI and MCP
  tools already do, so a list arrives as a tuple, `land_repository(root, apply="false")` previews as
  it selects, `prove_repository(root, {...})` no longer raises `AttributeError`, and a mapping whose
  `root` entry is the very `root` argument now runs where it is refused today.
- The console moves to `ethos.application.console` and the result projection to
  `ethos.application.result_projection`; `surface/runtime_identity.py` retires, every
  `resolve_root` importer changes one import line, and the fifteen import-linter rows go.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The command-plane specification already requires one typed operation for every transport.

## Impact

- `src/ethos/application/catalog.py`, `inspection.py`, `plan.py`, `adoption.py`,
  `land/operation.py`, `publication/operation.py` and `proof/operation.py`; the new
  `src/ethos/application/console.py` and `src/ethos/application/result_projection.py`;
  `src/ethos/cli.py`, `src/ethos/surface/cli/output.py`, `version.py` and `root_binding.py`, the
  `resolve_root` importers under `src/ethos/surface/cli/`, `src/ethos/surface/mcp/server.py`, and
  `.config/checks/import-linter/import-linter.toml`; `src/ethos/surface/runtime_identity.py`
  retires.
- Tests: `tests/unit/kernel/test_operation_catalog.py`,
  `tests/unit/application/test_proof_operation.py` and the patch retargets the design lists;
  adopters see no change to commands, flags, exits, JSON, the console script, `python -m ethos.cli`,
  the hook entry or the MCP tools.
