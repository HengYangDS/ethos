# Tasks

## 1. The actor of an invocation

- [ ] 1.1 Add `process_input` to the process adapter and make `selected_change` call it. Done when
      `tests/unit/adapters/openspec/test_selection.py` passes unchanged.
- [ ] 1.2 Add the flag, its help text, the step of a missing actor, `invocation_actor` and
      `handoff_step` to `src/ethos/adapters/actor.py`. Done when the four cases of
      `test_an_explicit_actor_binds_one_invocation_and_its_children` pass.
- [ ] 1.3 Take `actor` in `invoke` and `--actor` in every catalog command. Done when
      `test_the_actor_a_step_asks_for_is_supplied_by_its_flag` passes.
- [ ] 1.4 Give no actor option to a command that exits as its child does. Done when both cases of
      `test_every_token_after_the_end_marker_reaches_the_command` pass: the child of
      `ethos host run` receives `--actor` and its value with `--` and without it.
- [ ] 1.5 Read `--actor` in the shared argv selection on every command that takes it, through the
      function that the CLI's signature calls. Done when the four `--actor` cases of
      `test_an_argv_selects_its_declared_form_and_nothing_else` pass.

## 2. The continuations

- [ ] 2.1 Render the step of a missing actor and the handoff of a foreign one in the current
      authority. Done when the six cases of
      `test_public_surfaces_preserve_one_current_authority_recovery` pass, the run of the rendered
      handoff preview among them.
- [ ] 2.2 Render the same two steps in the linked retirement. Done when the `foreign_lease` case
      of `test_landed_topic_retirement_obeys_the_exact_resource_boundary` and the `missing_actor`
      case of `test_retained_topic_retirement_binds_the_surviving_ref` pass.
- [ ] 2.3 Name the actor as the input of its step in `src/ethos/application/invocation.py`, and
      delete `tests/unit/kernel/test_next_inputs_reader_first.py`. Done when each of the five
      commands returns the input, the operation behind the MCP `status` tool returns the same
      entry of name, flag and description, and `EthosResult.from_payload` returns the same step.
- [ ] 2.4 Render the handoff only from a Lease whose generation, expiry and holder can be read, and
      continue to the lane's status otherwise, in both callers. Done when the four cases of
      `test_a_lease_without_its_coordinates_renders_no_handoff`, both cases of
      `test_a_foreign_lease_without_its_coordinates_continues_to_lane_status`, the foreign case of
      `test_landed_public_actor_and_lease_state_matrix` and the three cases of
      `test_a_foreign_actor_is_offered_the_handoff_or_keeps_the_lane_status_step` pass, a
      blank target renders no step, a generation given as text names the step that its
      number names, and a retirement that found no lane keeps the status.
- [ ] 2.5 Pin that a step with no value to choose has no `inputs` member. Done when the six cases of
      `test_public_surfaces_preserve_one_current_authority_recovery` pass with that assertion.
- [ ] 2.6 Build the expected handoff of that test from the held Lease, read by its branch before
      the commands run. Done when its two cases of a foreign actor pass and run the preview.

## 3. Documents

- [ ] 3.1 State the flag and the two steps in the command reference, the packaged Skill, the
      quickstart and the Unreleased section of `CHANGELOG.md`, with the Breaking entry and its
      repair. Done when Prettier and the prose gate accept them and the reference holds at most
      500 nonblank lines.

## 4. Lane-only acceptance

- [ ] 4.1 Place the Added and the Breaking entry in the Unreleased section that follows the
      release of the reader. Done when the section that holds them does not also say that no
      command emits `inputs`.
- [ ] 4.2 Pass the precheck and readiness at the lane head. Done when each passes on the
      committed head.
- [ ] 4.3 Pass the full proof on the archived head. Done when its receipt names that head.

## Workflow follow-up

- The Git configuration overlay of appendix A.7 is carried by the draft Change `gate-environment`,
  whose proposal states the obligation.
- Continuations without `--holder-ref` are carried by the draft Change `lane-operations`, whose
  proposal states it.
- A missing-actor step that an MCP client can follow is carried by the draft Change
  `mcp-step-inputs`.
- Landing: the full proof runs on the archived head, and its receipt is the landing's.
