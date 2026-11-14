# Proposal

## Why

A proof's result depended on the shell that launched it. On 2026-11-14 one governed repository's
full proof failed its JavaScript behavior gate from a shell that had activated mise and passed
from a clean one, on the same head and the same runtime: a test of that repository runs
`mise exec -- npm --version` and received the npm that Node bundles instead of the locked one.
The adoption session bisected it to one variable. With `__MISE_DIFF` present in the gate child's
environment a nested `mise exec` orders its paths by the launching shell's activation; without it
the locked order holds.

The cause is ETHOS's own isolation. Eleven call sites remove the caller's `MISE_` variables from a
child and none removes the state that `mise activate` exports under `__MISE_`
(`__MISE_DIFF`, `__MISE_SESSION`, `__MISE_ORIG_PATH` and the shell hooks' markers). The eleven
sites each write the prefix as their own literal, so the rule had no single owner to correct. The
code is the same in every released runtime; a hosted job has no activation and never showed it.

The owner's rule of 2026-11-14 admits it to this batch: a defect that blocks a governed repository
does not count against the one off-gate row of a weekly batch.

## What Changes

- The Mise adapter names once what a child must not inherit, `MISE_` and `__MISE_`, and all eleven
  call sites use that name: the Python, Go and JavaScript gates, native supply materialization and
  the adapter's own probes.
- A test runs a child under a parent environment that carries activation state and requires that
  the child sees neither family, apart from what ETHOS itself sets.
- The Unreleased section of `CHANGELOG.md` gains a Fixed line.

Not breaking: a child that relied on the launching shell's activation state received an order
that the locked selection does not state.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ADDED requirement `Locked execution inherits no mise activation state`.

## Impact

`src/ethos/adapters/toolchain/mise.py`, `src/ethos/adapters/gates/code_quality.py`,
`src/ethos/adapters/gates/python_quality.py`, `src/ethos/adapters/gates/javascript/analysis.py`,
`src/ethos/adapters/gates/javascript/behavior.py`,
`src/ethos/adapters/repo/runtime/materialization/native_supply.py`, three test modules,
`CHANGELOG.md` and `openspec/specs/quality/spec.md` through this Change's delta.
