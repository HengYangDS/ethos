# Proposal

## Why

GitLab issue #2 (2026-11-04): when a gate times out, `ethos prove --json` lists
`gate_unknown:<gate>` and two consequence gaps, but not the gate's own `gate_timeout:<gate>`, and
the proof's verdict is `block` although the gate reported `unknown`. Two reviews traced a wider
defect. ETHOS has a result envelope but no rule for composing it from its parts. About thirty
aggregators and boundaries reduce by hand, and most of them drop a part's cause, keep only its
first gap, or turn `unknown` into `block`.

## What Changes

- A kernel `Outcome` holds a verdict, gaps, bounded causes and a next action. One `combine`
  reduces verdicts, `block` before `unknown` before `pass`, and unions the gaps. A part keeps its
  class code first and at most five of its own cause codes, and counts the rest.
- `OutcomeError` carries an `Outcome` across an exception, and `ProcessExecutionError` is one whose
  producer declares its verdict class. Every single-gap raise and failure helper carries the full
  gap tuple instead.
- The boundaries build their result from the carried `Outcome` through one
  `EthosResult.from_outcome`: `prove`'s gap emission, the process and public-contract failure
  results, and Git-effect compensation.
- `prove --execute` lists each failed gate's own cause codes after its class code, keeps `unknown`
  for a timeout, carries one bounded diagnostic per failed gate, and takes its next action from
  `remediation_for_gaps`.
- A dependent of an unknown prerequisite is `unknown`, and a dependent of a failed one is `block`.
- Status, Work Lane refresh, retirement and commit creation reduce their parts through `combine`.
- The undeclared-result gap becomes `gate_undeclared:<gate>`, so `gate_unknown` keeps one meaning.
- An architecture test refuses single-gap transport in product code.

Dry-run output, stored proof statements and check shapes do not change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `kernel`: results compose their parts' causes.
- `quality`: a timed-out gate reports `unknown`, and a dependent takes the class of its unmet
  prerequisite.

## Impact

- New `src/ethos/contracts/outcome.py`; `src/ethos/result.py` and `src/ethos/adapters/process.py`.
- The proof path, the gate runner, the shared failure boundaries and the aggregators that the
  design names, with their tests.
- Adopters that match `block` for a timed-out proof see `unknown`. Every class code stays.
