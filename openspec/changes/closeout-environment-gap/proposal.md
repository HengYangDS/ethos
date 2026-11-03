# Proposal

## Why

Closeout re-admits the candidate's proof from the candidate worktree, and
`resolve_proof_policies` compiles that worktree's committed policy with its repository Python
(`_repository_python` in `src/ethos/adapters/repo/gate_policy.py`). When the worktree has no
`.venv` and the policy runs a Python module gate, the compiled policy carries
`gate_runtime_missing:repository-python`, so its digest differs from the proof's. Admission then
reports only `proof_attestation_repository_policy_mismatch`, and closeout's next action repeats the
same closeout command.

- On 11-03 the closeout of `fa3afc148` failed this way after the candidate worktree's `.venv` was
  removed. Compiled from that worktree, the full floor's digest was `c35a669b…` instead of the
  proof's `ff5c6562…`. Recreating the environment with `uv sync --locked --group dev` restored
  `ff5c6562…`, and the closeout passed.

## What Changes

- Proof admission reports the runtime gaps of the policy it compiles, such as
  `gate_runtime_missing:repository-python`, instead of a policy mismatch.
- That gap carries a remediation hint: run the repository's bootstrap verb in the admitted
  worktree, then retry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: admission names a missing repository runtime instead of a policy
  mismatch.

## Impact

`_admitted_proofs` in `src/ethos/adapters/mutation/proof_admission.py`, `remediation_for_gaps` in
`src/ethos/adapters/mutation/remediation/guidance.py`, the proof admission tests and the changelog.
