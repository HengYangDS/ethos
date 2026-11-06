# Tasks

## 1. Native tool supply

- [x] 1.1 Require tools/ci to materialize native tools only through the repository's mise. Done when
      an architecture test fails on the direct calls and passes once the four call sites use
      `supply_tool`. The test failed first on four direct calls, and passes.
- [x] 1.2 Take `native.py`'s tool choices from the native supply registry. Done when a test that
      reads its usage finds every registered tool. The test failed first without Grype, and passes.

## 2. Per-commit inventory

- [x] 2.1 Catalog the kept archive on the host-conformance legs that match a release leg. Done when
      a projection test that compares those legs with the declared release legs passes and the
      projection conforms. The test passes, and 369 CI, delivery and supply tests pass.
- [ ] 2.2 Accept the per-commit inventory on hosted runners. Done when a proposal run's windows-x64
      leg on Python 3.14 and a dev run's legs on the release Python catalog their archives.
