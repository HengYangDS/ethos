---
name: ethos-quality-gate-governance
description: Use when changing ETHOS quality gates, CI, pre-commit hooks, lint, format, type checks, docstrings, coverage, config lint, shell lint, or proof gate registry policy.
---

# ETHOS Quality Gate Governance

## When to Use

Use this skill when work changes quality policy, gate registry entries, CI
provider files, pre-commit hooks, lint or format configuration, type policy,
docstring checks, coverage thresholds, or reusable quality scripts. The purpose
is to keep the active quality floor in one place and let CI and hooks remain
provider projections.

## Workflow

1. Read `AGENTS.md`, `rules/mutation.md`, `rules/evidence.md`,
   `docs/governance/product-design-contract.md`, and the relevant quality spec.
2. Reuse the declared gate graph and shared executor; keep native checks in
   Nox/Python and tool-native policy under
   `.config/checks/<concern>/` or the smallest stable native config owner.
3. Keep `pyproject.toml` limited to package/workspace metadata unless a tool has
   no better native owner.
4. Use `references/gate-design.md` to check SSOT, MECE boundaries, and hard-floor
   expectations before tightening or adding a gate.
5. Update `system/gates.toml`, native tool policy, CI, hooks, tests, and
   OpenSpec together; do not duplicate tool or command ownership.
6. Compare required coverage across product, tests, tools, carriers, packages,
   runtime/resources and provider projections. Inject representative failures
   through real owners; neither counters nor a clean audit prove effectiveness.
7. Prove the exact gate path with focused scripts first, then run head-bound
   `ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json`.

## Evidence

Apply the lifecycle skill's failure-escalation rule, then use owner scripts and
proof output:

```bash
uv run --frozen --offline python -m nox -s lint
uv run --frozen --offline python -m nox -s config_quality
uv run --frozen --offline python -m nox -s shell_lint
uv run --frozen --offline python -m nox -s prose
ethos prove --gate repository-audit --json
ethos prove --gate python-types --json
ethos prove --gate docstrings --json
# After the Nox `tests` session has produced current coverage evidence:
ethos prove --gate unit-architecture --json
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
```

## Trust Boundary

Repository truth remains the source of truth. Quality skills explain the gate
workflow. The gate registry, scripts, configs, tests, OpenSpec records, command
JSON, and HEAD-bound evidence are repository truth. CI, pre-commit, and hosted
runners are projections over those owners.
