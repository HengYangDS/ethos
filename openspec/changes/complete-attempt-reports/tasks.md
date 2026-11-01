# Tasks

## 1. Case identity

- [x] 1.1 Add an Allure case whose parameter id contains `::`. Done when it fails on the current
      derivation with `allure_identities_differ`. (`tests/architecture/test_allure_reporting.py`
      failed before the fix.)
- [x] 1.2 Name each executed case as allure-pytest does. Done when the new case and the existing
      Allure cases pass.
- [x] 1.3 Name the differing cases in the refusal. Done when the planted missing result is named.

## 2. Specification and verification

- [x] 2.1 Write the `quality` delta. Done when strict validation passes.
- [x] 2.2 Check the rule against the hosted results that the old rule refused. Done when every
      result of GitHub run 41312820863 that records its node identity is named alike: 7,779 of
      7,779.
