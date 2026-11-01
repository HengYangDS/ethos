# Proposal

## Why

The proposal run of `22f912c2c` (GitHub 41312820863, GitLab pipeline 13570) executed all 7,782 cases
without a failure, and hosted verification still refused it on both forges with
`hosted_allure_report_invalid:allure_identities_differ`.

- Exactly one of 7,782 Allure results differs from the executed cases:
  `tests/unit/kernel/test_coordination_contract.py::test_holder_ref_rejects_provider_only_or_ambiguous_values[agent::thread:id]`.
  allure-pytest 2.16.2 parses a node identity by splitting it on every `::`
  (`allure_pytest/utils.py`, `ParsedPytestNodeId`), so it reads `test_…_values[agent` as a class,
  and its `allure_full_name` then takes the test name from the item's original function name.
  `_allure_name` (`tools/ci/hosted_verification.py:279-283`) takes the function from the same split,
  `thread:id]`, so the two names differ.
- The defect was latent since `test-runner-unification` added the check. At `ab1ac7e26` the run
  stopped at its first failure, a missing gitleaks, as the accepted failure bound requires, before
  this case ran.
- The refusal names no case, so finding it required downloading all 7,782 results.

## What Changes

- Report admission names each executed case as allure-pytest does: package and classes from
  allure-pytest's own parser, the test from the case's original function name.
- A refusal names the first differing cases on each side.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: report admission names cases as their producer does and names the cases that differ.

## Impact

`tools/ci/hosted_verification.py`, `tests/architecture/test_allure_reporting.py` and the `quality`
specification.
