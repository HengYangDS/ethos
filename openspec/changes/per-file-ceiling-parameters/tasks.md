# Tasks

## 1. Contract and effective ceilings

- [x] 1.1 Set both `[size]` defaults to 500 and add the bound 1000 in
      `src/ethos/contracts/paradigm/paradigm.toml` and its model. Done when
      `tests/unit/contracts/test_repository_paradigm.py` asserts 500, 500 and 1000.
- [x] 1.2 Resolve the effective ceilings from `.ethos/rules.toml` `[paradigm.size]` in one owner
      under `src/ethos/repository/paradigm/`, reporting a restatement, a higher value without a
      reason, a value above the bound, a value that is not a positive integer, an unknown key and
      the retired `[quality.code_size]` table, and listing each reasoned deviation. Done when a test
      in `tests/unit/repository/test_paradigm_report.py` covers each row of design decision 1.
- [x] 1.3 Judge Python files in the paradigm report and current Markdown in docs health against the
      effective ceilings. Done when a declared lower value and a reasoned higher value change the
      verdicts in `test_paradigm_report.py` and
      `tests/unit/governance/validation/test_markdown_length.py`.
      (The 11 new cases failed before the change and pass after it, with the 109 existing cases
      of the three modules; the 21 test modules that import the changed modules pass, 658 tests.)

## 2. ETHOS meets the default

- [x] 2.1 Split the seven `src/` files above 500 effective lines by semantic ownership:
      `adapters/repo/git.py`, `domain/publication/inspection.py`,
      `repository/policy/references/commands.py`,
      `adapters/mutation/lane_lifecycle/work_lane_refresh.py`, `domain/publication/operation.py`,
      `adapters/admission/current/resolution.py` and `adapters/mutation/lane_lifecycle/merge.py`.
      Done when each module is at most 500 effective lines and the test modules of every importer
      pass. (Six modules split by concern, 1616 tests of their importers and the architecture
      suite pass; `git.py` fell to 473 when `retire-unreachable-product-code` removed
      `exact_rename_target`.)
- [x] 2.2 Split the four test modules and the two `tools/ci/delivery/acceptance/` modules above
      500 effective lines. Done when each is at most 500 and the moved tests still run. (No
      Python file in the tree exceeds 500; the moved tests and their importers pass, 946 tests.)
- [x] 2.3 Keep the product and test source budgets within their terminal totals. Done when the
      source-budget measurement of the lane head reports both within budget. (`python_product`
      69,862 of 70,000 and `python_tests` 89,575 of 90,000.)

## 3. Verification

- [x] 3.1 Run the paradigm report and docs health over ETHOS's tree with the candidate contract.
      Done when neither reports a size gap. (At 500, the paradigm report finds no size gap and
      docs health no length gap.)

## Workflow follow-up

- Archive this Change with the lane's other Changes, prove the archived head once, then land,
  close out and publish `dev` to GitHub and GitLab.
- After the release that carries it, rerun the fleet preview and send each affected repository's
  file list to the session that owns the repository.
