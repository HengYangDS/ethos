# Proposal

## Why

On 2026-11-11 ten Go provider tests failed on the workstation with
`compile: version "go1.27.3" does not match go tool version "go1.27.4"`. The fixture repositories
declare no mise tools, so the provider resolved `go` from `PATH`, Homebrew's 1.27.4. The agent's
shell still exported mise's `GOROOT` for 1.27.3, and `run_command` passes the ambient environment
through, so the 1.27.4 binary ran 1.27.3's compiler. With `GOROOT` unset all 73 Go tests pass. The
same leak reaches an adopter repository whose Go tool is not locked: a host setting selects a
different Go's tools than the executable ETHOS resolved, and the gate fails for a reason outside the
repository.

## What Changes

- The Go provider runs the `go` it resolved with that executable's own root. It removes an ambient
  `GOROOT` before running it; a locked tool graph that sets `GOROOT` still sets it.
- The four `go` invocations, package listing, the coverage probe, tests and vet, run through one
  helper, so the rule has one owner.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No verdict changes for a consistent host; a host whose `GOROOT` names another Go no longer
fails the Go gates.

## Impact

`src/ethos/adapters/gates/code_quality.py`, `tests/unit/adoption/quality/test_go.py` and
`CHANGELOG.md`.
