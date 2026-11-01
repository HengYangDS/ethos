# Tasks

## 1. One outcome owner

- [x] 1.1 Project a failed or timed-out command into its complete outcome in the process adapter and
      replace the six inline stream decoders with it. Done when both streams, an empty stream, a
      nonzero exit and a timeout each keep their exact values. (Covered in `test_process.py`.)

## 2. Boundaries

- [x] 2.1 Keep a provider's native command failure in `gate_provider_error`, and report an expired
      provider deadline as `gate_timeout` with its bound and elapsed seconds. Done when both cases
      are covered through the gate runner. (Covered in `test_runner.py`.)
- [x] 2.2 Raise Git's own failure from the text classification. Done when a refused Git keeps its
      exit status and stderr and an incomplete success still reads unobserved. (Covered in
      `test_git_attributes.py`.)
- [x] 2.3 Chain the Mise failure and record native command failures in the package acceptance's
      terminal evidence. Done when a failure with 2,140-byte streams keeps both streams complete.
      (Covered in `test_distribution.py` and `test_acceptance.py`.)

## 3. Specification

- [x] 3.1 Add the outcome requirement to the `quality` delta. Done when strict validation passes.
      (It passes.)
