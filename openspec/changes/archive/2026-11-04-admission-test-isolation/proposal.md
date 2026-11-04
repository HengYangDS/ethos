# Proposal

## Why

The second beta.2 full proof at `4c3cc0eba` failed one test:
`tests/unit/gates/test_proof_slot.py::test_a_full_proof_takes_the_host_slot_between_its_slot_and_load`.
The proof is itself admitted through the host queue that `host-admission` added, so it exports
`ETHOS_HOST_ADMISSION` and `ETHOS_HOST_CPU_CAP` to its gates. The test suite's per-test
environment did not remove them. Every test therefore inherited the outer proof's admission, and a
test that expects no admission saw one. Run outside a proof, the same tests pass. With the two
variables set, the failure reproduces.

## What Changes

- The suite's autouse hermetic environment removes the admission variables that the product
  exports, by the product's own names (`host_admission.TOKEN` and `host_admission.CPU_CAP`). A test
  that needs an admission sets one explicitly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Test isolation changes no requirement, so `skip_specs: true` applies.

## Impact

`tests/conftest.py`.
