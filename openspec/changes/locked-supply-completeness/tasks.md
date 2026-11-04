# Tasks

## 1. Completeness and containment

- [x] 1.1 Refuse a locked tool or environment whose declared supply is incomplete. Done when tests
      show that a declared tool reported as not installed, or with a missing install path, refuses
      both with `mise_supply_incomplete:<tool>@<version>`, that a complete node-only supply still
      resolves an undeclared npm, and that each new test failed before the change. The four
      missing-tool cases failed with `DID NOT RAISE` before; `test_mise_supply.py` now passes 10.
- [x] 1.2 Refuse an executable outside its own tool. Done when tests show that an executable that a
      declared tool names, but that resolves inside another tool's install path, refuses
      `locked_tool` and `locked_environment` with `mise_executable_outside_tool:<name>`. Both
      cases failed with `DID NOT RAISE` before.
- [x] 1.3 Name the next action that can help. Done when tests show the regression and an earlier
      Mise for a graph-referenced lock entry under Mise 2026.11.0, `mise trust` for an untrusted
      root, and `mise install --locked` otherwise. The three cases failed with `DID NOT RAISE`
      before. The environment checks completeness before `env --json`, whose warning would
      otherwise name `mise trust` under Mise 2026.11.0.
- [x] 1.4 Keep the other `run_mise` fakes truthful. Done when the toolchain, gate, adoption,
      materialization, projection and CI delivery tests that resolve locked supply pass. Three fakes
      now answer `ls --current --json` with the supply that their configuration declares, and the
      1,205 tests of those suites pass.

## 2. Specification and notes

- [x] 2.1 Write the `quality` delta. Done when strict validation and the cumulative archive
      simulation pass. Both pass, with all 12 specifications valid after the lane's three archives.
- [x] 2.2 Name the fix in the Unreleased notes. Done when the changelog validates. It validates
      with no error.

## 3. Acceptance

- [x] 3.1 Re-run the scratch probe with the lane's source. Done when the proxy resolves under Mise
      2026.11.0 and 2026.10.25, aigw-cli is refused under 2026.11.0 with the regression named, and
      aigw-cli resolves under 2026.10.25 with its root trusted. All four hold, and an untrusted
      aigw-cli under 2026.10.25 names `mise trust`
      (`build/runtime/work/locked-supply-completeness/scratch-1104/logs/*-v2-probe.json`).

## Workflow follow-up

- Send the Change to AIGW before landing, as agreed on 11-04.
