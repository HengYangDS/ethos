# Proposal

## Why

`ethos land` takes its candidate authority from the proof it admits, but it looks that authority up
under the Change it would select by default: the active Change, or the archive nearest the head. A
lane that archives several Changes can hold a valid proof of an earlier one. Proof admission accepts
that proof, because its carried Change still matches its exact archived source at the head, and
landing then refuses it with `proof_attestation_authority_binding_mismatch`. On 11-02 a lane that
archived three Changes was proved with the first; the refusal cost a second full proof, and the two
proofs then made every later step refuse `stale_binding` until `ETHOS_CHANGE` named one of them.

## What Changes

- Landing looks up its authority under the Change that the admitted proof carries, so the proof
  query and the candidate effect select the same intent.
- Proof admission is unchanged: it still checks the carried Change against its exact source at the
  head, the lane's archive scope and the proof policy. Landing still refuses a proof whose carried
  encoding is not admissible at the head.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: landing binds the intent that its admitted proof carries.

## Impact

`src/ethos/adapters/mutation/landing.py` and one landing test module. No new command, option,
receipt field or adopter configuration.
