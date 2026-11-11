# Tasks

## 1. Name the package when the manifest names no lane

- [x] 1.1 Give revoke import's subject rule. Done when a revoke whose package has no manifest
      blocks with `handoff_manifest_missing` and raised a validation error before the change. RED:
      the revoke raised `MutationSubject`'s `string_too_short` error for an empty resource; GREEN in
      `c234e3c1a`: the report names the resolved package path and blocks with
      `handoff_manifest_missing`.

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head. At `c234e3c1a`: the three impacted test files the go-own-root
      sweep did not cover ran 24 tests, all passing, the static precheck passed, and readiness passed
      28 of 28 gates.
