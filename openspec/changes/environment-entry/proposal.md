# Proposal

## Why

A result that needs the executor's identity tells the executor to take another's. Three
continuations render `export ETHOS_ACTOR=<holder>`: the current authority's answer to a missing
actor and to a foreign one, and a retirement's answer to a foreign one. An agent that runs the line
as written signs its work with the holder's name, and a second session that does the same shares
it. The release-candidate plan names the remedy (archived `rc-plan`, appendix A.7, and Change 7 of
A.11): the actor is the executor's own identity, from `--actor` with `ETHOS_ACTOR` as the declared
fallback; a missing actor yields an `instruction` whose `inputs` name it; and a mismatch continues
to the handoff, never to an `export`.

The archived `rc-scope-plan` puts the reader of `inputs` one release before its producers. The
reader landed in 0.2.0-beta.11 as the archived Change `2026-11-14-next-inputs-reader`. This row is
the producers, in the batch of 0.2.0-beta.12, whose named Breaking entry is that continuations drop
the actor export.

## What Changes

- Every catalog command takes `--actor <identity>`. It is the executor's identity for that
  invocation and its children, it wins over `ETHOS_ACTOR`, and it ends with the invocation.
  `ethos host run` alone takes none: it hands its words to a child command, as before.
- A result without an actor continues to the instruction
  `rerun the command with --actor <your own identity>`, and its `next.inputs` name the flag. It is
  the first producer of `inputs`, so the test module that pinned their absence is deleted.
- A result whose actor is not the Lease's holder continues to the `ethos lane handoff transfer`
  preview, with the Lease's exact coordinates and the executor as the target, as a decision for a
  person. This holds for the current authority (`lease_holder_mismatch`) and for a linked
  retirement (`foreign_work_lane_retire_authority_required`).
- **BREAKING**: no continuation renders `export ETHOS_ACTOR=<holder>`. Repair: a caller that ran or
  parsed that line passes its own identity with `--actor`, or keeps `ETHOS_ACTOR` set, and takes
  the handoff to the holder.
- The command reference, the packaged Skill, the quickstart and `CHANGELOG.md` say the same.

Not in this Change, each carried by a draft Change that the design names: the Git configuration
overlay of A.7 (`gate-environment`), continuations without `--holder-ref` (`lane-operations`), and
a missing-actor step in an MCP client's terms (`mcp-step-inputs`, which this Change creates).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: ADDED `The actor is the executor's own identity` and
  `A missing or foreign actor continues to its own step`; MODIFIED
  `A next step names the values that only the agent chooses`, whose first producer now exists.
- `repository-governance`: MODIFIED `Invocation and editor bindings have distinct remediation`,
  whose two actor scenarios now name their recovery step.

## Impact

- `src/ethos/adapters/actor.py`, `src/ethos/adapters/process.py`,
  `src/ethos/adapters/openspec/selection.py`, `src/ethos/adapters/admission/current/authority.py`,
  `src/ethos/adapters/mutation/lane_retirement/linked.py`, `src/ethos/application/catalog.py`,
  `src/ethos/application/invocation.py` and `src/ethos/surface/cli/catalog.py`.
- `tests/unit/adapters/test_actor.py`, `tests/unit/admission/current/test_public_projection.py`,
  `tests/unit/admission/current/test_resolution.py`, `tests/unit/cli/test_lane_retirement.py`,
  `tests/unit/cli/test_host_run.py`, two tests that pass the old line through as data, and the
  deleted `tests/unit/kernel/test_next_inputs_reader_first.py`.
- `docs/reference/command-plane.md`, `docs/guides/quickstart.md`, the packaged
  `ethos-repository-work` Skill and `CHANGELOG.md`.
- One bullet in each of the draft proposals `gate-environment` and `lane-operations`, and the new
  draft `openspec/changes/mcp-step-inputs/`.
- The results of every command that resolves the current authority, and of both linked
  retirements, when the actor is missing or foreign. No refusal is added and no exit code changes.
