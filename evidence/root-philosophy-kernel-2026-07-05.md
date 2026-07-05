---
subject: ethos:root-philosophy-kernel-evidence
role: evidence
state: active
relations:
  evidence_refs: tests/architecture, OpenSpec, Tao, kernel model
---

# Root Philosophy Kernel Evidence - 2026-07-05

## Scope

This evidence records the archived `root-philosophy-kernel-20260705` change.

Implemented changes:

- Promoted the compact ETHOS root verse into `system/tao.md` as the root
  generative constraint.
- Extended `docs/concepts/kernel-model.md` with a Root Philosophy Derivation
  that maps the verse to kernel obligations.
- Promoted an `ethos-core` OpenSpec requirement so future command surfaces,
  assistant projections, local models, adapters, profiles, tool frameworks, and
  proof hosts must derive from the existing kernel chain instead of becoming new
  truth centers.
- Added architecture tests that require the Tao, kernel model, and promoted
  `ethos-core` spec to preserve the operational anchors.
- Followed up by keeping `ETHOS` as the product name and `问道` as the root
  text, removing the line-by-line feature map from the Product Design Contract,
  preserving plain engineering names, and aligning the package documentation to
  the current `ethos-core` plus `ethos` topology.

## Operational Mapping

The promoted interpretation is operational, not decorative: hidden authority,
one kernel, domain-fit measure, and boundary-preserving growth.

## Verification

Commands run from `/Users/yheng/projects/ethos-work-root-philosophy-kernel`:

```bash
uv run --group dev pytest -q \
  tests/architecture/test_product_design_contract.py::test_tao_and_kernel_model_carry_root_philosophy_as_generating_constraint \
  tests/architecture/test_product_design_contract.py::test_product_design_contract_operationalizes_root_philosophy
openspec validate --all --strict
ethos quality claims --json
ethos openspec --lifecycle --json
uv run --group dev pytest -q tests/unit/governance/test_docs_registry.py
uv run --group dev pytest -q
```

Observed focused results on 2026-07-05:

- Root philosophy architecture tests: `2 passed`.
- OpenSpec strict validation: `9 passed, 0 failed`.
- Claims gate: `ok=true`, `state=clean`.
- OpenSpec lifecycle: `ok=true`, `state=clean`, active change count `0`.
- Docs registry focused suite: `9 passed`.
- Follow-up docs/product-boundary focused suite:
  `58 passed` for `tests/architecture/test_product_design_contract.py`,
  `tests/architecture/test_product_boundaries.py`, and
  `tests/unit/governance/test_docs_registry.py`.
- Docs registry command: `ok=true`, `state=clean`.
- Work-lane status and changed-plan commands: `ok=true`, no required gaps.

Full-suite snapshot on 2026-07-05: `542 passed, 4 failed`. The four failures are
outside the root-philosophy lane and match existing governance/parity/fixture
surfaces: report parity gaps, capability-profile lifecycle fixture validation,
policy-exception waiver state, and product parity gaps. The accepted full-suite
verifier remains `uv run --group dev pytest -q`; bare `python -m pytest -q` is
not used as product proof because it does not load the managed dev CLI dependency
set.

## Limits

This is semantic/docs/spec/test substrate only. It does not start or modify
Codex, Claude, Hermes, MCP, local model, IDE, TUI, browser, or app processes.
