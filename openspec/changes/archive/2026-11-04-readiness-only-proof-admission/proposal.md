# Proposal

## Why

A full executing proof runs its readiness gates first, the planned gates that are neither test nor
package gates and depend on none, then waits for its repository's proof slot and for the host load
to fall within the admitted limit before it runs the remaining gates. The proof enters that wait
even when its plan holds no remaining gate, so a proof of static or governance gates alone waits for
host capacity that nothing it still has to run needs.

- On 11-03 the release journey's fixture adopter, whose full proof set is two Git gates, ran them,
  then held its proof slot and waited for host load until the journey's 600-second command timeout
  ended it on a busy workstation. An adopter whose proof runs only static checks waits the same way
  and, once the wait outlasts the admission bound, ends with `proof_admission_contended`.

## What Changes

- A full executing proof enters admission only when a gate remains after its readiness gates. A
  proof that plans only readiness gates runs them without waiting for the proof slot or host load,
  and its result records no admission.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a full proof that plans only readiness gates does not wait for host-load admission.

## Impact

`src/ethos/surface/cli/root/proof.py`, the proof execution tests and the changelog. Proofs that plan
a test or package gate wait exactly as before.
