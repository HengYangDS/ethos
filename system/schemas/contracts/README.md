# system/schemas/

JSON Schema and TOML schema contracts — the Contract layer's machine-checkable
shapes. The terminal design moves the legacy `schemas/` root here.

Authority: docs/plans/terminal-governance-product-design.md (§`system/`).
Migration state (Phase A): directory created; relocation of `system/schemas/kernel/*`
(37 files) here is a separate, independently-revertible step, coordinated with
updating the ~6 py files that reference `schemas/ethos`.
