# Design: ethos-docstring-quality-gate-20260705

## Context

The official OpenSpec boundary is `ethos-quality`. The repo-local product
boundary is the existing quality gate model: ETHOS decides why a quality gate
runs, `.config/checks/<concern>/` owns how the gate is configured, CI invokes
reusable scripts, and `system/tools.toml` records the tool/gate catalog.

## Design

Use an in-process ETHOS policy check instead of adding `docstr-coverage`,
`pydoclint`, or another dependency at this stage. The gate scans configured
package source roots and counts only public product surfaces:

- package boundary `__init__.py` docstrings;
- CLI command functions decorated by a command app;
- explicitly exported functions/classes declared through `__all__`.

The gate reports stable JSON through `ethos quality docstrings --json`:
coverage percentage, documented count, public count, missing symbols, and
required gaps. The CI script invokes that command; the threshold lives only in
`.config/checks/docstrings/policy.toml`.

## Alternatives

- Reusing Ruff `D` rules directly was rejected for the first hard gate because
  the current package roots produce hundreds of public/private docstring-style
  findings, forcing noisy helper docstrings rather than product-surface intent.
- Copying alternate mechanism corpus's full docstring stack was rejected as premature for ETHOS:
  ETHOS can absorb the separation of concern and coverage threshold idea without
  adding a parallel toolchain.

## Proof Strategy

- Architecture tests verify config ownership and CI script projection.
- CLI tests verify `ethos quality docstrings` output and blocking gaps.
- Gate registry tests verify the gate is part of default and full proof graphs.
- Runtime evidence records focused tests, Ruff, script execution, and report
  readiness.
