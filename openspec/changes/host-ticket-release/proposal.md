# Proposal

## Why

A model review of the release diff, `v0.2.0-beta.10..dev`, returned nine findings on 2026-11-15.
Two of them are in the host admission that a foreground host proof gained after 0.2.0-beta.10.
Both were reproduced by a failing regression before any product code changed. This Change repairs
them ahead of the release Change of 0.2.0-beta.11, whose tag is planned for 2026-11-21, so that
release does not carry them.

- A wait for the host queue that ends without admission keeps its ticket. The released
  0.2.0-beta.10 left the queue in one `finally` that also covered the wait. The commit `a20bbaa3e`
  split the wait from the admitted body, and the wait lost the release. Three exits skip it: the
  wait's bound, an OS error while waiting and an interrupt. The ticket then stays live in that
  process, ahead of every later arrival and listed by `ethos host status`, while the raised error
  is referenced and after that until the interpreter's collector frees the lock. Its record and
  lock file stay until the next waiter removes them.
- A host proof runs its readiness tier before it asks for the host ticket. When the admission is
  refused, its result reports `executed: false` and no check. The readiness results that ran are
  lost, and nothing names the gates that did not run.

## What Changes

- `admitted_host_work` gives its place up on every exit, also one that ends the wait.
- A host proof whose admission is refused keeps the results of the readiness gates that ran and
  names the other gates in `data.not_run`. Its verdict, its gap and its exit are unchanged.
- One regression for each of the three exits, and one for each of three refusals of a host
  proof: the bound, an absent host root and an unwritable queue. The test of a bounded wait again
  requires that only the holder's record remains, as it did in 0.2.0-beta.10.

Not breaking: neither defect is in a release. For a refused host proof, `data.executed` becomes
true, and `data.checks` and `summary.gate_count` hold the readiness gates.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement's text is wrong, so `skip_specs: true` applies. The quality requirements
`Heavy local work is admitted host-wide` and `Full proofs and nested work share the host admission`
state the bound, the gap and the exit, which this Change keeps; they are silent on the two
behaviors that the regressions now pin.

## Impact

`src/ethos/adapters/gates/host_admission.py`, `src/ethos/application/proof/host.py`,
`tests/unit/gates/test_host_admission.py`, `tests/unit/cli/test_host_gate_proof.py` and
`CHANGELOG.md`.
