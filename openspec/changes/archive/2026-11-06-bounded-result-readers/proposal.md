# Proposal

## Why

Since `result-contract` landed, an ETHOS result over its budget keeps only its small `data` entries
inline and names a digest-bound detail file for the rest. Two places in ETHOS run another ETHOS
process and read its `data` straight from stdout:

- Landing's predecessor policy probe runs the installed runtime's `prove --full --json` and reads
  `data.transition_plan` (`adapters/mutation/proof_admission.py`).
- Reference-transaction admission runs the candidate's `hook ref-transaction` and returns its
  `data` as the report (`adapters/repo/hook/admission.py`).

`CURRENT` became a schema-3 build at the agent-native landing. Since then the probe's result is
always over budget and its plan sits in the detail file. So every self-hosted landing blocks with
`predecessor_policy_probe_invalid`, first seen when hosted-expand's preview was refused at 04:21 on
2026-11-07. The candidate reader loses any moved entry the same way.

`expand_result` has a second problem: it also validates the full result against the reader's own
model. A result from a build whose result vocabulary differs would therefore refuse even when its
digest matches.

## What Changes

- `expand_result` returns the full result as its producer wrote it. It verifies that result
  against the digest and size the bound names, and against every field the bound keeps. A caller
  that needs this runtime's model validates the expanded result itself, as the delivery acceptance
  reader already does.
- The predecessor probe and the candidate reader expand a bounded result before they read it. A
  detail that is missing or disagrees refuses with each reader's existing gap.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: an ETHOS operation that reads another ETHOS process's result reads it in full.

## Impact

- Source: `src/ethos/result.py`, `src/ethos/adapters/mutation/proof_admission.py`,
  `src/ethos/adapters/repo/hook/admission.py` and `docs/reference/command-plane.md`.
- Tests: `tests/unit/kernel/test_result_bound.py`, `tests/unit/kernel/test_proof_admission.py` and
  `tests/unit/adapters/repo/hook/test_execution.py`.
