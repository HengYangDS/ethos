# Tasks

## 1. Run the resolved Go with its own root

- [ ] 1.1 Remove an ambient `GOROOT` from every `go` invocation through one helper. Done when the
      real-Go behavior test with `GOROOT` set to an empty directory fails before the change and
      passes after, and the four call sites use the helper.

## 2. Acceptance

- [ ] 2.1 Pass the precheck, the impacted sweep and readiness at the lane head. Done when each
      passes on the committed head with `GOROOT` and `GOBIN` exported as the agent shell exports
      them.
