# Proposal

## Why

Readiness refused the lane on 2026-11-12 with
`source_budget_terminal_exceeded:python_product:80175>80000`. The growth since DR-0020 is
essential: the owner's rules of that day for Markdown lists, canonical text and package markers,
the foundation starter that passes its own paradigm, and the RC families that DR-0020 counted.
DR-0010 moves the ceiling by one 5,000 step only after proved duplication and dead code are gone,
and the owner's 2026-11-01 rule lets the agent take that step with the evidence.

## What Changes

- Removed first: the staged layout checks merge into one module (45 line-equivalents), and the
  unreferenced `binds_custody` is deleted.
- DR-0025 records the necessity review, and the product ceiling in
  `.config/checks/format-selection/policy.toml` moves one step, from 80,000 to 85,000.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The native source-budget declaration owns the number, so `skip_specs: true` applies.

## Impact

`.config/checks/format-selection/policy.toml`, `src/ethos/adapters/store/custody.py`,
`docs/decisions/dr-0025-product-budget-step-85.md` and the decisions index.
