# Tasks

## 1. The contract and its readers

- [ ] 1.1 Add `NextInput` and `NextStep.inputs`, absent from the wire when empty, and add both to
      the tracked result schema. Done when the tracked schema equals the model's schema and the
      kernel result tests pass with their expected bytes unchanged.
- [ ] 1.2 Keep the carried inputs in `EthosResult`: `next_inputs`, the computed `next`,
      `from_payload`, and `replace` for the runtime and payload-budget copies. Done when
      `test_a_reader_keeps_the_inputs_of_a_carried_step_and_only_them` passes and the three
      malformed inputs of `test_a_reader_re_derives_next_and_never_trusts_a_carried_one` refuse.
- [ ] 1.3 Add one test over the readers of `next`. Done when
      `test_every_reader_keeps_the_inputs_a_step_carries` reads one synthetic result through the
      model, its bounded copy, the acceptance reader and the tests' CLI support, and the result
      schema accepts that result.
- [ ] 1.4 Pin that no producer names the inputs. Done when
      `tests/unit/kernel/test_next_inputs_reader_first.py` passes, and fails when a third product
      module names `NextInput` or `next_inputs`.

## 2. Documents

- [ ] 2.1 State the reader rule in the result envelope of `docs/reference/command-plane.md` and add
      the Added line to the Unreleased section of `CHANGELOG.md`. Done when Prettier and the prose
      gate accept both and the reference still holds at most 500 nonblank lines.

## 3. Lane-only acceptance

- [ ] 3.1 Pass the precheck, readiness and the full proof at the lane head. Done when each passes on
      the committed head.
- [ ] 3.2 Pass `local-install-smoke` at the lane head. Done when the installed build's
      `EthosResult.from_payload` reads the status result in the installed-package check.
