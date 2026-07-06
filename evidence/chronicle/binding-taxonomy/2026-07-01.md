---
subject: ethos:evidence:binding-taxonomy
role: evidence
state: active
relations:
  supports: ethos-coupling-governance
---

# Binding Taxonomy Evidence - 2026-07-01

This evidence records the local ETHOS binding-taxonomy correction batch.

## Scope

- Classified Git, branch roles, and worktree lifecycle as product-semantic hard
  bindings.
- Classified OpenSpec as a mandatory official governance dependency while
  keeping the official OpenSpec CLI as an adapter execution surface.
- Classified JSON Schema, command JSON, TOML, JSONL, and ignored SQLite local
  state as native protocol bindings.
- Classified the current Python workspace, uv, Hatchling, pytest, Ruff, and
  package build workflow as self-hosting toolchain bindings rather than adopter
  ontology.
- Kept hosted forge, editor, model, MCP, ACP, npm, Superpowers, Backlog, and CI
  surfaces in profile or adapter binding space.

Remote publication was intentionally out of scope.

## Verification

Commands run from `work/binding-taxonomy`:

```bash
uv run --group dev pytest tests/unit/test_coupling_governance.py tests/unit/test_cli_contracts.py::test_quality_coupling_audit_reports_git_native_boundary tests/architecture/test_product_design_contract.py::test_product_design_contract_canonizes_kernel_first_principles tests/architecture/test_product_design_contract.py::test_product_design_contract_keeps_git_native_not_generic_vcs tests/architecture/test_product_design_contract.py::test_canonical_product_docs_are_provider_neutral -q
uv run --package ethos ethos quality coupling-audit --json
uv run --group dev pytest -q
uv run --group dev ruff check .
uv build --all-packages
uv run openspec validate --all --strict --json
```

Observed results:

- Focused RED/GREEN target set: `6 passed`.
- Coupling audit: `ok=true`, `required_gaps=[]`, with Git in
  `product_semantic_hard_binding`, OpenSpec in
  `mandatory_governance_dependency`, native protocols in
  `native_protocol_binding`, and self-hosting proof tools in
  `self_hosting_toolchain_binding`.
- Full pytest: `264 passed`.
- Ruff: all checks passed.
- Package build: all workspace packages built as sdist and wheel.
- OpenSpec strict validation: `8` specs passed, `0` failed.
