# Design

## Context

See the [proposal](proposal.md). Line references are to this Change's base, `4a5029e96`.

What the journey runs for each predecessor P and the subject N:

- `upgrade_from` and `prove_upgrade` (`tools/ci/delivery/acceptance/journey.py:159-196`) install P
  offline and call `prove_retained_upgrade` (`runtime.py:311-446`). Its order is: N coordinates, P
  by name, retained state seeded under P, N by name, a rollback to P, N again, then authoring in
  the lane, which ends with N's repair of the retired publication fields (`brownfield.py:258`,
  `:279-299`).
- The one rollback runs before the repair, from the canonical root. That root is never repaired:
  the repair is a `git apply` to the lane's working files
  (`src/ethos/adapters/mutation/carrier_edit.py:283-291`), and nothing commits it.
- The result ends with three constants, each the string `not_qualified` (`runtime.py:442-445`).
  The third is `rollback_after_declaration_repair`. No tracked file reads that key:
  `grep -rn rollback_after_declaration_repair src tools tests docs` finds its writer alone.
- The retained fixture declares no pin: its Mise configuration holds settings and tasks only
  (`adopter_content.py:66-69`).
- The install smoke calls the same function with a predecessor runtime (`effect.py:356`).

What the product does:

- A named runtime other than the invoking build is probed first. The target's own publish
  readiness reads the root's tree, and the activation refuses with
  `runtime_rollback_declaration_repaired` where the target names
  `publication_topology_declaration_invalid`, or with `runtime_rollback_root_behind_accepted`
  where the root's HEAD lacks the accepted tip (`src/ethos/adapters/repo/hook/rollback.py:49-59`).
- The probe precedes the receipt (`hook/activation.py:255` before `:257`), so a refused rollback
  is refused the same way with and without a reason.
- A departure from the accepted pin needs a reason and a lane and leaves a receipt under the Git
  common directory; a repository whose accepted branch declares no pin departs from nothing
  (`src/ethos/adapters/repo/runtime/pin_selection.py:117-149`). While the pin and the lane's ref
  last, a transition keeps the selection and reports `runtime_selection_open` (`:98-99`); the
  first transition without a named runtime after either ends deletes the receipt (`:192-208`,
  `hook/activation.py:251`).
- A transition follows a newer pin only where Mise names the pinned release's install
  (`pin_selection.py:111-114`, `:177-189`), and the product finds Mise on the path alone
  (`src/ethos/adapters/toolchain/mise.py:257-262`).
- The declaration has two formats. `src/ethos/repository/release/publication.py`, as
  `git show v0.2.0-beta.5:<path>` prints it, gives a declaration without the two command fields
  the gap `publication_topology_declaration_invalid`. The same file at each tag from
  `v0.2.0-beta.6` to `v0.2.0-beta.10` and at the base (`:21-23`, `:83`) gives that gap to neither
  form: it reads a declaration without the fields and names each field of one that holds them as
  retired.

What the journey's qualification gives a child: a path that holds Git and the signing tool
(`journey.py:67`, `:298`), installations from a `file://` table under the key `http:ethos`
(`tools/ci/delivery/distribution.py:393-396`), and no installation of the pin, which acquisition
removes (`acquisition.py:344`).

## Goals / Non-Goals

Goals:

- For each predecessor, the journey's receipt states what the product decided about a rollback
  after the repair, from a step that ran.
- The journey's own snapshot of the retained repository is compared around that step.
- What the journey still does not run is named in the receipt by its own key.

Non-Goals:

- Product code. The plan's name `runtime_rollback_open` and a receipt that a landing deletes are
  not built; decision 6 reads the plan by the product.
- A pin in a fixture, a receipted rollback and landings in the journey. Decision 1 names their
  slices.
- The refusal as release evidence. No release that a governed repository selects gives it, so it
  is covered by its unit test and taken by the journey only when a dispatch names such a
  predecessor.
- The install smoke's result, and the two other constants: interruption recovery and uninstall
  while a consumer runs.

## Decisions

1. **The plan's four steps are three slices, and this row builds the first.**
   - **Rests on:** the step-by-step reading in the proposal, and these sizes by the product's own
     measure (`ethos.measure`, with the tokens per line of
     `.config/checks/format-selection/policy.toml`). The first slice's leg is 94.0 tool
     line-equivalents on a sketch that passes the linter and was not run. One in-process pass of
     the four steps, with two doubles, is 184.4 test line-equivalents. Every other size here is an
     estimate.
   - **Considered:** the plan as written, at an estimated 350 to 450 tool and 250 to 350 test
     line-equivalents: it needs a pin and a lock in the fixture, Mise on the stage's path with
     installs keyed by the pin, a helper that lands three times for each predecessor, once under
     the predecessor's console, and a subject that ships the receipt; and its step 2 has no
     predecessor that refuses. The receipt alone, in a second fixture that declares the subject's
     pin, at an estimated 110 to 150 and 130 to 190: no subject that the base knows as published
     ships the receipt. No change to the journey, keeping the in-process pass as a regression:
     the receipt and the release entry then keep their line.
   - **Chosen because:** the first slice is the only one that fits the row's 130 and 80, runs on
     releases that are published today, and ends the constant with a result that a step
     computed. The trade-off is that the row does not show the plan's refusal and receipt in the
     journey; the product's own tests show them in process.
   - **Applies to:** this row. The second slice, the receipted rollback in a fixture that declares
     a pin, is read again at the cut of 0.2.0-beta.14, when a published subject ships the
     receipt. The third, a pin followed across landings, is read with `release-rehearsal`, whose
     job the plan gives the predecessors through the pin's own key.
2. **The step selects the held rollback from the repaired lane, with the subject's console.**
   - **Rests on:** the lane is the one tree that holds the repair; its HEAD contains the accepted
     tip, which the preflight requires (`hook/rollback.py:53-56`); and the fixture declares no
     pin, so the selection needs no reason (`pin_selection.py:128-129`). The accepted requirement
     `Status names the supported rollback` names this command: the selected runtime's
     `hook install --root <root> --runtime <ROLLBACK>`.
   - **Considered:** asserting the plan's refusal, which fails on every release since
     0.2.0-beta.6; a second rollback from the canonical root, whose tree still holds the
     predecessor's fields, so it repeats the step that already runs; committing the repair and
     landing it first, which is the third slice; and running the command that `status` names
     for the lane, which is the same request at the cost of one more request and a parse of its
     text.
   - **Chosen because:** it is the rollback that an operator runs after the repair, on the tree
     where the preflight decides, and it costs two requests.
   - **Applies to:** the journey's retained adopter after its authoring step. The lane is found by
     the branch that the upgrade's own result names, and the runtime by the repository's
     `ROLLBACK` selector, read with the product's reader.
3. **Two decisions pass, and anything else fails the leg.**
   - **Rests on:** the preflight's three gaps and the selection's own (`hook/rollback.py:55-58`,
     `:76`; `pin_selection.py:135`).
   - **Considered:** recording any other answer as unknown and passing the leg, which would keep
     an unqualified rollback behind a passed journey; and failing on a refusal too, which would
     stop a dispatch that names a predecessor older than 0.2.0-beta.6.
   - **Chosen because:** `admitted` is checked by its effects (the selector names the held
     runtime, the retained repository is equal, and the subject is selected again with the
     selector, the hooks path and the hook files as before), and `refused` by its code and by
     nothing having changed. A probe that could not answer, a root behind the accepted tip or a
     changed byte is a defect of the product or of the fixture, and the leg fails with the
     product's own answer in its message.
   - **Applies to:** each predecessor of a leg. The trade-off is a new way for a release's
     journey to fail; the first end-to-end run of decision 7 shows whether it does.
4. **The step is one new module, and the journey alone calls it.**
   - **Rests on:** the product's count of effective lines, of which the paradigm refuses a file
     above 500: `runtime.py` 495, `brownfield.py` 493, `adopter.py` 465, `journey.py` 286.
   - **Considered:** extending `prove_retained_upgrade`, as the plan says, whose module has five
     lines left and which has a second consumer; and a flag on it that the install smoke leaves
     off.
   - **Chosen because:** `prove_upgrade` in `journey.py` calls the leg after the retained upgrade
     and merges its result, so the smoke's result does not change and no file nears its limit.
   - **Applies to:** the release journey. The install smoke's successor is a development build and
     keeps the constant.
5. **The result stays flat, and each remaining limit gets its own key.**
   - **Rests on:** the result's three string constants today, and the one writer of the key.
   - **Considered:** an object under the key, which changes its type for a reader outside the
     repository; and a new key beside an unchanged constant, which leaves `not_qualified` in a
     leg whose rollback passed.
   - **Chosen because:** `rollback_after_declaration_repair` becomes `admitted` or `refused`, a
     string as before, and two new strings beside it say what is left: `receipted_rollback` and
     `pin_across_landings`, both `not_qualified` until their slices land.
   - **Applies to:** the `upgrade_and_rollback` entry of each predecessor in the journey's
     receipt.
6. **Names and requirements follow the product.**
   - **Rests on:** `grep -rn runtime_rollback_open src tools tests docs openspec/specs`, which
     finds nothing; the `pin-selection` design, which records the name `runtime_selection_open`
     for both receipt kinds; and the accepted scenario `The accepted pin changes`, in which the
     next transition deletes the receipt.
   - **Considered:** a delta that renames the state or deletes the receipt at the landing, which
     is product code; and a delta to `distribution` for the first slice.
   - **Chosen because:** the requirement on the releases that a beta's journey starts from asks
     for "an upgrade, with its rollback", and the first slice adds evidence under those words
     without changing them.
   - **Applies to:** the first slice, which keeps `skip_specs: true`. The second and third slices
     add a scenario to that requirement.
7. **One dispatch runs the changed journey end to end.**
   - **Rests on:** the `release-journey` job of `.github/workflows/ci.yml`, whose condition
     (`:627`) admits a dispatch with `journey_tag` on any ref and which runs the journey of the
     checked-out tree. The newest tag in the base's clone is `v0.2.0-beta.10`
     (`git tag --list 'v0.2.0-beta*'`).
   - **Considered:** a local run, which reaches the forge from the releasing host and is one
     platform.
   - **Chosen because:** the dispatch runs every declared leg on the forge's runners.
   - **Applies to:** the ref that holds the changed journey, with `journey_tag` `v0.2.0-beta.10`
     and `journey_previous` `v0.2.0-beta.9`; and again with the first subject whose dispatch
     names two predecessors.

## Risks / Trade-offs

- **The row does not build the plan's four steps.** It builds the part that a published release
  can run, and names the rest in the receipt and in the release entry.
- **The first end-to-end run decides the admitted path.** That each release since 0.2.0-beta.6
  reads a repaired declaration is a reading of the loader at each tag. No predecessor's console
  was run on the lane's repaired tree, which also holds the subject's repair of the branch roles.
  A predecessor whose probe cannot answer there fails the leg with
  `runtime_rollback_probe_failed`.
- **Time.** An estimated 10 to 28 seconds for each predecessor on each leg: two requests of
  `hook install`, which took 4.6 to 14.3 seconds each in the retained adopter on the three hosted
  legs of the journey of 0.2.0-beta.10 from 0.2.0-beta.9, generated on 2026-11-17 and read from
  the legs' stage events. Those legs' stages sum to 209.6 to 225.3 seconds. A refused rollback is
  one request.
- **The test size is an estimate.** 80 to 110 line-equivalents covers the two decisions, five
  failing cases and the journey's merge. The stop rule for tests is 120.
- **A receipt key's values change.** A reader outside the repository that compares
  `rollback_after_declaration_repair` with `not_qualified` reads a passed step as intended; one
  that lists the allowed values needs the two new ones.
- **Three interpreters.** The leg reads a selector with path predicates and starts two product
  processes and several Git processes, each under the helpers' existing time bounds. Its tests
  run on Python 3.12 and 3.13 before the row's review closes.
