## Context

`run-config-lint.sh` bootstraps into the repository-owned Python runtime, but
two inline standard-library validations still invoke a bare `python` command.
That creates a host alias dependency outside the runtime contract. The same
Change also removes a duplicated accepted OpenSpec requirement, not a second
scope mechanism: OpenSpec remains the official Change lifecycle and
`scope.toml` remains ETHOS-owned companion data.

## Goals / Non-Goals

**Goals:**

- Resolve inline configuration validation through the existing bounded
  interpreter contract: `ETHOS_PYTHON`, then `PYTHON`, then `python3`.
- Preserve TOML, JSON, YAML, Taplo, and whitespace checks, including targeted
  invocations with no JSON or YAML inputs.
- Preserve the single scope-binding requirement and every fail-closed coverage
  and bootstrap scenario it already defines.
- Demonstrate isolated, sharded full-test execution without changing the
  coverage floor, timeout, or test selection.

**Non-Goals:**

- Adding a new Python toolchain, changing provider CI semantics, loosening
  quality gates, changing official OpenSpec schemas, or mutating DDWG.

## Decisions

1. Use a local shell variable initialized from the same explicit override
   chain already used by the Python test owner script. `python3` is the stable
   system command fallback; a bare `python` alias is not part of the contract.
2. Keep the existing inline standard-library checks. Replacing them with a
   third-party parser would widen toolchain and supply-chain scope without
   solving the alias defect.
3. Retain the later, fully specified material-change requirement as the single
   accepted text, and merge the earlier scenarios that add legacy-profile
   bootstrap detail. The duplicate heading is deleted rather than renamed into
   a second authority.
4. Treat the isolated full suite as verification of existing evidence-isolation
   behavior. Its output remains ignored generated evidence; the Claim records
   the bounded commands and their final results rather than promoting raw logs.

## Risks / Trade-offs

- [An explicit interpreter is invalid] → the script still fails closed at the
  actual interpreter invocation and does not silently switch runtimes.
- [A spec merge loses a bootstrap boundary] → the delta carries the complete
  retained requirement and the focused scope suite remains required.
- [Sharded evidence is stale] → the owner script binds shard reuse to the
  captured HEAD and the final proof is separately HEAD-bound.
