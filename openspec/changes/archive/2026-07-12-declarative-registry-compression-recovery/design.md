# Design

```text
system/*.toml -> strict frozen Pydantic contract -> pure ordered projection -> adapter overlay
```

`system/coupling.toml` owns stable coupling taxonomy, bindings, metadata, and
static projection fields. `system/standards.toml` owns standards-adapter facts.
Both are force-included as package resources for installed execution. Pydantic
rejects unknown fields, duplicate identifiers, malformed records, and missing
adapter admission before a public projection is emitted.

Only live branch-role, toolchain, and release-profile facts remain in Python
adapters. The old static dictionaries and `_adapter` wrapper are deleted.
Declaration-projection test matrices prove that every static declared field
reaches the existing public registry shape; focused tests prove the live overlays.
