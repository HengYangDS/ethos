# Tasks

## 1. Per-tool completeness

- [x] 1.1 Bind the completeness check to the tools that a resolution returns. Done when tests show
      that a declared tool not yet installed, whose executable nothing resolves, blocks neither
      another locked tool nor the environment, and that the existing wrong-tool cases still
      refuse; the new test failed before the change. It failed with
      `mise_supply_incomplete:gitleaks@8.30.1`; the 12 supply tests pass. In a store holding only
      CUE, `locked_tool("cue")` now resolves as on `dev`, which was hosted CI's failure.
- [x] 1.2 Name a missing tool when `mise env` warns about it. Done when a test shows that the
      warning becomes `mise_supply_incomplete` with the remedy that can help, and the test fails
      without that handling. The whole-supply check made it pass before; with the warning branch
      removed from the narrowed check, it fails.

## 2. Specification, notes and acceptance

- [x] 2.1 Modify the `quality` requirement. Done when strict validation and the cumulative archive
      simulation pass. Both pass, with all 12 specifications valid after the archive.
- [x] 2.2 Correct the `0.2.0-alpha.30` notes. Done when the changelog validates with
      0.2.0-alpha.30 as its target. It validates with no error.
- [x] 2.3 Re-run the scratch acceptance. Done when the proxy resolves under Mise 2026.11.0 and
      2026.10.25, and aigw-cli is refused under 2026.11.0 with the regression named. Both hold, and
      a trusted aigw-cli resolves its locked npm under 2026.10.25
      (`build/runtime/work/locked-supply-completeness/scratch-1104/logs/*-v3-probe.json`).
