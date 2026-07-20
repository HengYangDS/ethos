# Tool Adoption Catalog SSOT Design

## Decision

`system/tools.toml` is the sole declaration of a quality tool's identity,
profile, adoption state, optional gate, and adapter-only boundary. The Python
quality layer reads that file at the repository root and projects its entries
without recreating tool records in source.

## Projection

The `quality tool-profiles` payload keeps the stable `tool_adapters` envelope.
Each entry uses its catalog concern as `id`, exposes the catalog tool string as
both `tool` and `standard`, and preserves config, profile, adoption, gate, and
declared optional fields. This lets callers enumerate the complete catalog
without inferring status from missing fields or a `planned` boolean.

`quality asset-policy` reuses the same projection, so its schema instance and
the standalone tool-profiles command cannot diverge. The quality-profile schema
therefore validates the catalog-derived adapter envelope, while the tools
contract rejects a catalog entry missing a declared adoption state.

## Adoption States

- `active`: admitted mechanism with its declared current boundary.
- `candidate`: intentionally tracked for admission work, not a default gate.
- `deferred`: intentionally postponed and not a default gate.
- `rejected`: explicitly recorded as unavailable for product admission.

The schema accepts all four states. The current catalog need not invent a
rejected mechanism merely to exercise the enum.

## Verification

The regression reads the TOML catalog and asserts a one-to-one projection,
including optional gate presence and absence of the retired `planned` field.
Focused CLI, schema, and kernel tests validate the command and product-schema
paths. Configuration lint validates the changed TOML and JSON contracts.

## Rollback

Revert the catalog status fields, schemas, projection, and regressions together.
No external tool, provider, or remote state needs recovery.
