# Design

## Context

Three places decide what `ethos adopt` reports about the accepted pin:

- `adopt_existing`, the operation, renders the one continuation. `adoption_plan`, the planner,
  returns `runtime_selection`; on a refusal that holds the gap and the refusal's `next_action`.
  The gap reaches `required_gaps`. The action reaches nothing.
- `_runtime_plan` resolves what `--select-runtime` would select: `follow_accepted_pin`, then
  `expected_runtime_build`. Hook activation's `_supply_selection` makes the same two calls and
  then, for a pinned or named install, calls `require_installed_runtime` and `rollback_preflight`
  before anything is pinned.
- `_pin` of the exit plan returns `None` for a repository without the pin, and also when it cannot
  read the Mise configuration, parse it or delete the pin's line.

Which of activation's two checks adoption already makes was read from the functions it calls.
`expected_runtime_build` calls `require_installed_runtime` for a repository whose profile is not
the product's own, and `materialize_runtime` calls it for every installed runtime at apply.
`rollback_preflight` had one caller, `_supply_selection` (a search for `rollback_preflight(` in
`src`). The regression agrees with both readings: a damaged pinned install already refused in the
plan, and an install that refuses the root's declaration was selected.

## Goals / Non-Goals

Goals:

- A refused selection names what settles it.
- Adoption selects no pinned install that hook activation refuses.
- An exit that keeps the Mise configuration says so and why, in its plan and after its apply.
- The check that activation and adoption share has one owner.

Non-Goals:

- One resolver of the whole selection shared by activation and adoption; decision 2 records why
  only the check is shared.
- Deleting a pin that is not a line of its own. `without_field` deletes one field on a line of its
  own, and the exit keeps what it cannot delete exactly.
- Refusing an exit because the Mise configuration cannot be read.

## Decisions

1. **A refused runtime selection continues with the refusal's own next action.**
   - **Rests on:** the cases `unattested` and `not-installed` of
     `test_adoption_refuses_a_selection_as_activation_does_and_names_its_repair`, which received
     the adoption request where the repair belongs; the scenario
     `The pinned release is not installed`; `install_hook_runtime`, which returns a refusal's next
     action as it is.
   - **Considered:** the repair followed by the request, as a conflict is rendered; it keeps the
     root in the text, but two of the four repairs are prose that already ends in a command, and
     one refusal would read differently from the two commands. Letting the planner return the
     public next action; the requirement `Adoption continuation preserves request meaning` gives
     that to the operation.
   - **Chosen because:** the request cannot pass until the repair is done, and the refusal's owner
     already words the repair. The cost is that the repair of an unattested pin names no root, as
     it does from `hook install`.
   - **Applies to:** a plan whose `runtime_selection` carries a `next_action`, which only a refusal
     writes. A refusal without one, such as a damaged install, keeps the request, and a conflict
     still puts its own sentence first. The choice is a helper beside `adopt_existing`, which
     measures 14 against the threshold of 15 that `tests/architecture/test_decision_density.py`
     reads with `complexipy`.
2. **One function requires an installed runtime that accepts the root's declaration, and the
   adoption plan and hook activation both call it.**
   - **Rests on:** the reading in Context; the case `declaration-repaired`, where an authorized
     apply reached materialization for an install whose probe refuses; the scenario
     `A newer pin is installed`; and the import graph, read with `grimp`: neither module that the
     function needs, the runtime's selection and its build authority, reaches the rollback module,
     and no module is both above and below it.
   - **Considered:** the two calls repeated in `_runtime_plan`; the behavior then has two owners,
     which the finding itself names. The function in the runtime's selection module; that module
     would import the hook package, which imports it. One resolver of the whole selection shared
     with `_supply_selection`; it needs a `settle` parameter, a named-runtime branch and the
     departure receipt, which adoption has no use for. The check in `_apply_runtime` alone, where
     the finding points; a preview would pass and ask for an authorized apply, which would then
     end as `unknown`.
   - **Chosen because:** `require_accepting_runtime` sits beside `rollback_preflight`, takes the
     root and the runtime's path and returns the validated selection, so activation keeps its
     receipt. Measured with `complexipy`, `_supply_selection` stays at 4 and `_runtime_plan` gains
     its one branch, 6 to 7. `adoption_plan` computes `_runtime_plan` first in every call and
     reaches `_apply_runtime` only without a gap, so one probe covers a preview and an apply.
   - **Applies to:** a pinned or named install that a transition would select. A selection left in
     place is not probed, and `rollback_preflight` returns at once for the invoking build. Three
     test patches that named the two calls in activation now name them in the rollback module.
3. **The preflight's refusal names the request, not one command.**
   - **Rests on:** `RESTORE_ACTION` has two raise sites, both in `rollback_preflight`, and its
     text has no copy: a search of `src`, `tests`, `docs`, `rules` and `openspec/specs` for its
     last clause finds the constant alone.
   - **Considered:** keeping the clause that names the installation; a repository that adopts with
     `--select-runtime` to keep its own hooks would be told to run the installation, which
     replaces its hooks path. A second text for adoption; two owners of one refusal.
   - **Chosen because:** repeating the request from the lane is true for both callers and keeps
     one text.
   - **Applies to:** both refusals that carry the text, `runtime_rollback_root_behind_accepted`
     and `runtime_rollback_declaration_repaired`, from either command.
4. **The exit plan's `pin` names a configuration that the exit keeps.**
   - **Rests on:** the cases `unparsable`, `both-keys` and `dotted-key` of
     `test_an_exit_removes_only_the_pin_that_adoption_wrote`, each of which planned `None`; the
     two consumers of the plan's `pin`, both in `_apply_fenced`.
   - **Considered:** a blocker that refuses the exit; a broken Mise configuration would hold a
     repository in adoption, though restoring the Git configuration and removing the selectors
     read no Mise file. A second plan member for the kept case; every exit plan would gain it and
     change its digest. Naming only a text that is not TOML and staying silent where the pin's
     reader refuses; that needs a second parse, and a text with both pin keys can still hold the
     pin that adoption wrote.
   - **Chosen because:** `pin` keeps one meaning, what the exit does about the pin: `after` is the
     text it writes, and `kept` is why it writes none. A plan that removes the pin or finds none
     is unchanged, its digest included.
   - **Applies to:** a configuration that cannot be read (an operating-system error, bytes that
     are not UTF-8, text that is not TOML, or a refusal of the pin's reader) and a bare pin that
     is not one line under `[tools]`. A path that names no file, the options form and the legacy
     table plan no pin, as before. The reason is the reader's gap, the error's text or
     `pin_not_on_its_own_line`; it is a value of the plan and not a gap. The apply adds the file
     to its effects only when the plan names `after`.
5. **An applied exit that kept the Mise configuration names it in its next action.**
   - **Rests on:** the three kept cases of `test_an_exit_removes_only_the_pin_that_adoption_wrote`,
     each of which applied and continued with the bare status command; the form of the adoption
     conflict, an instruction, then "; then" and the command; `derive_next_step`, which reads
     prose as an instruction.
   - **Considered:** the kept file in `residue`; that member lists generation paths that the exit
     could not remove, and a tracked file is none. A gap on the applied result; an exit that did
     apply would read as blocked. Only the plan's `pin`; the result's own continuation would not
     name the step that did not run.
   - **Chosen because:** an agent follows `next`, and the one step left is the owner's: remove the
     pin by hand. The text names the file's path and the reason and ends with the status command
     that follows every exit. `data.pin` and the plan's digest do not change.
   - **Applies to:** an applied or resumed exit whose plan's `pin` carries `kept`. The preview's
     next action stays the exact apply request, and an exit that removed the pin or found none
     continues with status as before. The choice is a helper beside `_apply_fenced`, which
     measures 13 against the threshold of 15.

## Risks / Trade-offs

- `adopt --select-runtime` runs the pinned release's publish readiness once when it would select
  an install of another build, as `hook install` does. A target that cannot answer refuses with
  `runtime_rollback_probe_failed`. That code is raised through `RollbackRefusalError` and is not in
  the gap registry; this Change gives it a second emitter and does not register it.
- An exit previewed by a build without this Change, for a repository in a kept state, meets a
  digest mismatch at apply and is sent back to the preview. The pin removal is unreleased, so no
  shipped preview is affected.
- A kept reason from the operating system carries the file's absolute path, as the generation
  plan's `unknown` does.
- After an exit that kept the pin, `next` is an instruction without an argument vector. A reader
  that runs only commands stops there, which is the intent: the pin is the owner's to remove.
- Between the plan and the apply of one call, `_apply_runtime` resolves the pin again. A selector
  removed in that window could turn a kept selection into the pinned install of the same build
  without a second probe. Activation has the same window between its preflight and its selection.
