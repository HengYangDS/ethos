# Tasks

## 1. Contract

- [x] 1.1 Replace `coverage-xml` and `ruff-json` with `cobertura-xml`, `lcov` and `sarif`, make the Nox report optional and drop the per-session output bundle, then regenerate the gate schema; done when generic declarations validate and removed names, a second Nox report, a Nox report argument mismatch, duplicate producers and nested paths are refused. Evidence: 57 gate contract and 19 schema regressions pass.

## 2. Report Parsing

- [x] 2.1 Read Cobertura line counts with optional branch counts, LCOV line records, and SARIF results, notifications and scan inventory in the repository policy layer; done when kcov-shaped Cobertura, LCOV, SARIF level defaults, inventory roles and malformed reports pass their regressions. Evidence: 34 format regressions pass.

## 3. Judgment

- [x] 3.1 Judge one retained attempt's reports by axis in `native/evidence.py`, keeping the declared Nox, pytest event and Python runtime checks; done when a gate without a Nox report passes and failed tests, measured but unexecuted files, unbound coverage, SARIF findings and unknown SARIF scope block. Evidence: `test_script_reports_are_judged_by_property` and the format regressions.
- [x] 3.2 Claim only covered files in `code_quality` and `python_quality`, run ETHOS's own checks only for gates without native outputs and leave languages without such a check unclaimed; done when a native script behavior gate and ETHOS's own static check jointly discharge both axes and an uncovered file still leaves the obligation unproven. Evidence: `test_public_proof_joins_native_script_behavior_with_ethos_static`.
- [x] 3.3 Move the Nox producer fixtures to `cobertura-xml` and Ruff SARIF; done when their existing falsifying cases still block with their gaps. Evidence: 31 Nox regressions pass.

## 4. Documentation

- [x] 4.1 Document the native output formats and their judgment in the repository profile contract and the changelog; done when the documentation checks pass. Evidence: Prettier and markdownlint pass.

## Workflow follow-up

- Prove the exact head, then land, close out and publish to both peers.
- openai-responses-proxy (session 210a1fe7): rename `coverage-xml` to `cobertura-xml` and write Ruff SARIF when it moves its runtime pin.
- Ordo: add a kcov-measured script behavior gate, then remove `excluded_script_paths`, through its own lane.
