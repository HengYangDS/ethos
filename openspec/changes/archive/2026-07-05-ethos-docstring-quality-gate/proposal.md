# Proposal: ethos-docstring-quality-gate-20260705

## Why

ETHOS already gates Python tests, coverage, lint, formatting, typing, imports,
security, and docs, but public Python product surfaces can still lose their
intent-bearing docstrings without a dedicated gate. That is a small drift signal:
reader-facing API intent becomes hidden while tests remain green.

## What Changes

- Add an ETHOS-owned public-surface docstring coverage gate.
- Keep policy in `.config/checks/docstrings/policy.toml` and CI invocation in a
  reusable `.config/ci/scripts/run-docstring-coverage.sh` script.
- Register the gate in quality profiles, gate registry, `system/tools.toml`, and
  hosted CI.
- Limit the first hard gate to product-visible Python surfaces: CLI commands,
  explicit exports, and package boundary docstrings.

## Capabilities

- `ethos-quality`: subject=python-public-surface-docstrings; reuse=extend; change=add; facet:lifecycle=validation; facet:surface=cli; facet:surface=ci; facet:surface=docs; facet:surface=openspec; facet:authority=source; facet:authority=test; facet:authority=docs; facet:authority=claim; facet:authority=evidence

## Out Of Scope

- No new external docstring dependency.
- No blanket requirement for every private helper to carry a docstring.
- No migration of tool policy back into `pyproject.toml`.
