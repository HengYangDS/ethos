# Tasks

## 1. Run the resolved Go with its own root

- [x] 1.1 Remove an ambient `GOROOT` from every `go` invocation through one helper. Done when the
      real-Go behavior test with `GOROOT` set to an empty directory fails before the change and
      passes after, and the four call sites use the helper. RED: the behavior test with a foreign
      `GOROOT` blocked with `quality_behavior_go_package_scope_unavailable`; GREEN in `4786ff201`:
      `_run_go` runs package listing, the coverage probe, tests and vet, and the module's 43 tests
      pass.

## 2. Acceptance

- [x] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head with `GOROOT` and `GOBIN` exported as the agent shell exports
      them. The impacted tests ran 1,608 at `4786ff201` and 24 more at `c234e3c1a`, all passing;
      the static precheck passed, and readiness passed 28 of 28 gates at `c234e3c1a`. The runs
      unset `GOROOT` and `GOBIN` as the kit does; the behavior test sets a foreign `GOROOT` itself,
      which is the exported case.
