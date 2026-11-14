# Proposal

## Why

A result's typed next step cannot yet say which values only the agent can choose. The
release-candidate plan gives that to `next.inputs` (archived `rc-plan`, Decision 2, Family 2, row A7
`environment-entry`; Appendix A.3 and A.7): a placeholder makes `next` argv-less, and a missing
actor yields an `instruction` whose `inputs` name it. Today the step model is closed, so a build
refuses a result that carries `inputs` as malformed. The plan therefore ships the reader first:
"readers accept `delegation` and `inputs` a release before producers emit them" (A.9). Decision 6 of
the archived `product-form-plan` repeats it for A7 and the routed first step (N1), and item R1 of
the release-candidate gate needs it. In the release-candidate scope that the owner approved on
2026-11-14 this reader ships in beta.11, and the producers follow in beta.12.

## What Changes

- `next` may carry `inputs`: one entry for each value that only the agent can choose, with the
  request field's `name`, its `flag` and its `description`, as the operation catalog names them. The
  member is absent when it is empty, so every result of today keeps its bytes.
- Every reader accepts and keeps it. `EthosResult.from_payload` re-derives the rest of the step and
  keeps the carried `inputs`; the result schema admits the member; the copies that name the runtime
  and bound the payload keep it; the delivery acceptance reader and the tests' CLI support read a
  result that carries it.
- No command emits `inputs`. One test module pins that, and the Change that adds the first producer
  deletes it.
- The command-plane reference states the reader rule, and the Unreleased section of `CHANGELOG.md`
  gains an Added line.

Not Breaking: readers accept more than before, and nothing is emitted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: ADDED `A next step names the values that only the agent chooses`; MODIFIED
  `The structured next step derives from the exact rendered argv`, whose readers now keep the
  `inputs` of a carried step.

## Impact

- `src/ethos/contracts/next_step.py`, `src/ethos/result.py`,
  `src/ethos/application/result_projection.py` and `system/schemas/kernel/result.schema.json`.
- `tests/unit/kernel/test_result_next_step.py`, the new
  `tests/unit/kernel/test_next_inputs_reader_first.py` and
  `tests/unit/ci/delivery/test_continuation.py`.
- `docs/reference/command-plane.md` and `CHANGELOG.md`.
- Out of scope: every producer of `inputs`, `--actor` and the rest of `environment-entry`, the
  guidance that tells an agent how to supply an input, and the `delegation` authority, which moved
  to 0.3.0.
