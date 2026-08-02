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
2. Put reusable commands in `tools/ci/scripts/` and tool-native policy under
   `.config/checks/<concern>/` or the smallest stable native config owner.
3. Keep `pyproject.toml` limited to package/workspace metadata unless a tool has
   no better native owner.
4. Use `references/gate-design.md` to check SSOT, MECE boundaries, and hard-floor
   expectations before tightening or adding a gate.
5. Update `system/tools.toml`, gate registry code, CI, hooks, tests, and
   OpenSpec together; do not duplicate command bodies across provider files.
6. Run the repository audit so owner shape, coverage, docstrings, and type
   policy drift are visible before claiming CI strength.
7. Prove the exact gate path with focused scripts first, then run head-bound
   `ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json`.

## Evidence

Apply the lifecycle skill's failure-escalation rule, then use owner scripts and
proof output:

```bash
tools/ci/scripts/run-python-lint.sh
tools/ci/scripts/run-config-lint.sh
tools/ci/scripts/run-shell-lint.sh
ethos prove --gate repository-audit --json
ethos prove --gate python-types --json
ethos prove --gate docstrings --json
# After `tools/ci/scripts/run-python-tests.sh` has produced coverage.xml:
ethos prove --gate unit-architecture --json
ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
```

## Trust Boundary

Repository truth remains the source of truth. Quality skills explain the gate
workflow. The gate registry, scripts, configs, tests, OpenSpec records, command
JSON, and HEAD-bound evidence are repository truth. CI, pre-commit, and hosted
runners are projections over those owners.
