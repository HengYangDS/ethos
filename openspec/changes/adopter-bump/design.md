# Design

## Context

See the [proposal](proposal.md) for this Change's place in the order.

What exists at the base:

- `ethos.repository.release.pin` owns the pin. It reads a Mise configuration in either form and
  renders the release's bare entry: the pin line under `[tools]` and
  `locked_verify_provenance = true` under `[settings]`.
- Adoption merges that entry into the configuration, adding lines and replacing none. A
  configuration that selects another release or holds the `http:ethos` table is an
  `adoption_conflict`. No operation moves an existing selection.
- Runtime selection follows the accepted pin, and a lane that runs a successor records a
  `successor` receipt (`pin-selection`).
- `ethos lane repair-paradigm` derives one plan from a list of gaps. A handler per obligation
  turns its carrier's text into the repaired text and may name a follow-up. The apply asks one
  exact-path prewrite admission for the native patch of every edit, writes it and names the
  follow-ups without running them.
- Prewrite refuses a generated output in an authored patch
  (`generated_projection_patch_required`): generated files enter only as the complete patch that
  `ethos lane project` previews. This repository's CI projection names the Mise configuration
  and the lock among its compiler inputs (`.config/checks/ci-projection/policy.toml`), so a
  projection preview is exact only after the selection is written and the lock is current.

The files of a bump, by kind. The counts are the committee's reading of 2026-11-14 for one
release in seven lanes, 79 files; this Change read no governed repository and did not measure
them again. "Product" names the operation that writes the kind.

| Kind of file                        | Read | Writer before         | Writer after          |
| ----------------------------------- | ---- | --------------------- | --------------------- |
| Pin entry in the Mise configuration | 13\* | hand                  | product: `--pin`      |
| Mise lock                           | 13\* | Mise, started by hand | Mise, named with root |
| Generated pipelines                 | 18\* | product: projection   | same, named in order  |
| CI model source                     | 18\* | hand                  | hand                  |
| Other configuration                 | 6    | product: repair, hand | same patch as the pin |
| Change record (OpenSpec files)      | 32   | hand                  | hand                  |
| Changelog line and other Markdown   | 9    | hand                  | hand                  |
| Test                                | 1    | hand                  | hand                  |

\* The reading counts pin and lock files together, and the CI model with its generated
pipelines. The CI Mise bootstrap is part of a generated pipeline, so it moves with the
projection. The reading calls the 32 record files and the 9 Markdown files "written by hand":
41 of 79. No pin writer touches them, so this Change does not bring that measure to 0.

Variants compared. Sizes are line-equivalents as the source-budget gate counts them.

- **F, a new verb `ethos lane bump`** with its own plan, digest, receipt, relock run and changelog
  writer. Product +243.8, tests +175.8, measured by this row's first preparation on the base of
  2026-11-14 and not measured again; it had no handler for the older form, no first pin and no
  block. A caller runs one preview and one apply. One receipt of its own. It leaves the Change
  record and other prose to the hand, and it previews the projection check without writing the
  generated files.
- **R, `--pin` on the repair plan for bare pins only.** This patch without the branch for the
  older form: product +164.7, measured here by counting the handler's tokens without that branch;
  tests not measured. A caller runs the preview, the apply, the relock and the projection. No
  receipt of its own. It also leaves the replacement of the `http:ethos` table to the hand, which
  the copies run of 2026-11-15 read in seven of thirteen governed trees.
- **A, adoption moves an older bare pin.** Product +9.0, measured here by applying the first
  preparation's three-line edit to this base's adoption text; tests about +10, an estimate. A
  caller runs the adoption preview and its apply with the head and the plan digest. No receipt,
  and no lane prewrite: adoption writes outside the repair plan. It reverses "adding lines and
  replacing none" of the requirement `Minimal Adoption Binding`, and it leaves the older form
  and every repair to the hand or to a second command.
- **R with the handler for the older form, chosen.** Product +169.1, tests +204.7, measured here
  against `ba9a1046d`. By part: the branch for the older form 4.4; the block of a newer selection
  26.1 in three functions; adoption's named next step 25.6 in two. A caller runs what R's caller
  runs. No receipt of its own. It leaves the Change record, the changelog line and other prose,
  the test and the CI model's source to the hand.

## Goals / Non-Goals

Goals:

- One operation declares the release's bare entry in every readable tree: over an older bare
  pin, over the older form and where no selection exists, in a Work Lane, in the same admitted
  patch as the repairs that the release asks for.
- The preview names every file that the apply writes, and the apply names in order every step
  that it leaves.
- A selection never moves to an older release, and a request that would move it there blocks.
- No audit, proof, landing or publication depends on the release that reads the repository.

Non-Goals:

- Writing the bump lane's Change record or its changelog line. Neither has a writer in this
  Change; a separate row decides a writer for a bump's record. Until then the measure "files
  written by hand per bump" stays above 0.
- Running Mise or the projection. Locking contacts the network and Mise writes the lock; the
  projection has its own previewed patch and authorization.
- A pin with options and a second carrier: only `.config/mise/config.toml` is read.
- Retiring the `http:ethos` declaration that a release publishes: `http-retirement` does that.

## Decisions

1. **The bump is a request to the repair plan, `--pin`, with one handler for every movable
   selection.**
   - **Rests on:** the comparison above; `repair_paradigm` in
     `src/ethos/adapters/mutation/paradigm_repair.py`, which makes one `apply_carrier_edits` call
     and therefore asks one admission for every edit of a plan; the handler's measured share of
     +4.4 for the older form.
   - **Considered:** F, which adds a second editor of the pin's carrier beside adoption and the
     repair plan and its own receipt; A, which is smallest but has no lane admission, changes
     what adoption promises and composes with no repair; R without the handler, which leaves the
     seven trees on the older form to the hand.
   - **Chosen because:** the repair plan already previews, admits and writes carrier edits, so the
     selection becomes one more edit of one patch, and the common-rule repair that the
     common-base design asks of the bump is a handler of the same plan. Accepted: the command
     `repair-paradigm` now also serves a request that no paradigm gap raises.
   - **Applies to:** the selection in `.config/mise/config.toml`. It does not cover a pin with
     options or a configuration that holds both forms; both stay reported.
2. **The move builds the release's bare entry with the merge that adoption uses.**
   - **Rests on:** the merge is one function, `with_bare_entry` in
     `src/ethos/repository/paradigm/repair.py`, which adoption's plan and the move both call;
     `tests/unit/adoption/test_pin.py`, whose plan rows pass unchanged.
   - **Considered:** a pattern over the pin line that keeps its quotes, spacing and comment, which
     the first preparation needed thirteen spellings of tests to bound; setting both keys of the
     entry without a merge, which would overwrite a provenance setting that the repository set to
     another value.
   - **Chosen because:** the bare entry has one definition and one writer. An older bare pin is
     set in place by the plan's own setter, and the `http:ethos` table is dropped with its
     sub-tables by the plan's own table remover; the merge then adds what is missing and refuses
     what it would have to replace. Accepted: the pin line is written in the canonical spelling,
     so a comment on that line goes, and removing the table closes runs of blank lines.
   - **Applies to:** the table in the form that a release published. A table in another spelling
     stays a reported gap.
3. **Only a request asks, and the target is the invoking release.**
   - **Rests on:** `pin_gap` and `pin_ahead` have one caller each, behind `--pin` (a search of
     `src/` for their names); `is_release_build`, which adoption uses for the same question.
   - **Considered:** a pin obligation in the paradigm report, which would make every release
     report every repository that pins its predecessor; a `--to <version>` argument, which the
     product could not verify against any installed release.
   - **Chosen because:** an upgrade is a decision of the repository, not a gap that the reading
     release imposes, and the release that runs the lane is the one whose rules and repairs the
     plan applies. A development build is no version that Mise could install, so it names no
     target and only reports.
   - **Applies to:** the command with `--pin`. Without it the command, the paradigm report and
     every proof read as before, so the Change is not breaking.
4. **A selection moves up only, and a request against a newer selection blocks.**
   - **Rests on:** `packaging.version.Version`, which orders `0.2.0-beta.9` before
     `0.2.0-beta.11` where text order does not (checked in this clone's interpreter); the exit
     kinds that the catalog declares for a preview and an apply
     (`src/ethos/contracts/operations/declaration.py`).
   - **Considered:** a reported obligation under a passing verdict, where a pass that planned
     nothing reads as a done bump; moving the selection in either direction, which silently
     downgrades a repository when an older console runs the command; blocking the pin alone and
     applying the plan's other repairs, which would write an older release's repairs into a tree
     that selects a newer one.
   - **Chosen because:** the request is refused before any plan. The result is a block with the
     gap `runtime_pin_ahead:<version>`, registered in the gap table, and its next action runs the
     same request with the release that the tree selects, through Mise, as the repository's own
     jobs run ETHOS. The handler refuses a newer selection a second time by itself. A refusal of
     a request made through a new opt-in option is no new rule for a tree, so the law freeze
     admits it: no tree reads differently without `--pin`.
   - **Applies to:** both forms, with `--pin` only. The preview states the block and, as every
     preview of this command, exits zero; the apply exits non-zero. A development build names no
     target and therefore compares nothing.
5. **The gap's carrier is the configuration path, and the release reaches the handler as an
   argument.**
   - **Rests on:** `paradigm_repair_plan`, which reads a carrier up to its first colon as a path;
     the other carriers of the toolchain owner, a path or a path and a key.
   - **Considered:** the release joined to the carrier, which is no path; the release read back
     from the gap's repair sentence by a pattern, which makes prose a data channel.
   - **Chosen because:** the plan takes the handlers that a request adds as a parameter, so the
     command binds the release and the relock into its handler and the gap carries only what a
     gap carries. Accepted: `paradigm_repair_plan` gains one optional parameter.
   - **Applies to:** requested obligations. The handlers of reported gaps stay in their table.
6. **The result names the steps that the apply leaves, in order, and runs none.**
   - **Rests on:** the two facts of Context about generated files; four other continuations of
     the product that name Mise's directory with `--cd` (a search of `src/` for that flag).
   - **Considered:** running the relock, which contacts the network and makes a failed lock a
     partial apply; putting generated files into the same patch, which prewrite refuses; running
     the projection check inside the preview, whose result would be stale before the relock.
   - **Chosen because:** the pin's gap leads the plan, so `mise --cd <root> lock` is the first
     follow-up and the next action after an apply, from any working directory. Where the
     repository tracks a projection declaration, `ethos lane project --root <root> --json` follows
     in the result's actions. Naming that step after the relock is enough, because its inputs
     include the lock. Accepted: the drift of generated files is named, not shown.
   - **Applies to:** an apply that wrote the selection. A second preview names neither step; a
     pin whose lock lacks the attested entry is then reported by runtime selection as
     `runtime_pin_unattested`. A retained topic's rename ends the command before any plan, so
     under `--pin` its result continues to the same request: the apply with `--pin` until the
     rename is done, and the preview with `--pin` after it. Its other fields are the rename's.
     A rename that stopped part way is finished by the same apply, so it keeps `--pin` too.
     A refused rename names its apply again, as it does without `--pin`, and so does a
     recovery that is itself refused, which reports the state of a rename that stopped
     part way; that step is the rename's own, and `refusal-repairs` holds its repair.
7. **No digest and no receipt of this Change's own.**
   - **Rests on:** `apply_carrier_edits`, which derives the patch again at the apply and refuses a
     preimage that changed (`carrier_edit_preimage_changed`); the `successor` receipt of
     `pin-selection`.
   - **Considered:** a plan digest between preview and apply, as adoption has; a receipt of the
     bump under the Git common directory, as F wrote.
   - **Chosen because:** the plan is a function of the carriers' text and the invoking release,
     and the admission binds the exact patch. The lane's record of the release it runs is the
     `successor` receipt that it already writes when it selects that release, and the written
     pin is in the lane's commit. A second record would have a second owner.
   - **Applies to:** the pin move. The projection step keeps its own head and patch binding.
8. **The Change record and the changelog line stay with the hand.**
   - **Rests on:** the reading above, 32 record files and 9 Markdown files of 79;
     `src/ethos/repository/release/changelog.py`, which validates and writes nothing; the first
     preparation's changelog writer, measured at +43.5 product.
   - **Considered:** a writer of one fixed changelog line, which adds a second sentence where a
     repository edits one sentence in place; a writer of the bump's Change record, which must
     satisfy each repository's own OpenSpec rules and has no measured design.
   - **Chosen because:** neither has a converged text, and a record writer is a row of its own.
     This Change removes the pin from the hand and names the lock and the projection steps; it
     does not bring "files written by hand per bump" to 0.
   - **Applies to:** every bump lane until that row lands.
9. **A tree without a selection gets its first pin through the same patch.**
   - **Rests on:** the copies run of 2026-11-15, which read no selector in six of thirteen
     governed trees; the shared merge of decision 2, which adds the entry to a configuration
     without one and is the whole text of a new one.
   - **Considered:** sending such a tree to `ethos adopt`, which is a second operation with its
     own digest outside the lane's admitted patch for six of thirteen trees.
   - **Chosen because:** one operation then serves every readable tree, and the first pin is in
     the same admitted patch as the release's repairs. The move reads the working file, so a
     configuration that an apply created reads as current before the lane stages it.
   - **Applies to:** a configuration with no ETHOS entry and a tree with no Mise configuration,
     which the apply creates. Adoption's own pin step for a repository that is not yet adopted
     does not change. A pin with options is its author's and stays reported, as adoption's exit
     leaves it. A configuration that exists and cannot be read as text is no tree without a
     selection: the plan's own reader decides what is absent, the move stays reported with the
     file named, and nothing is compared or planned for it.
10. **Adoption's conflict names the move.**
    - **Rests on:** `adoption_plan`, which reports `adoption_conflict` for a Mise configuration
      that the merge refuses; `pin_move`, which decides whether the lane repair replaces that
      selection; the requirement that the planner owns no public next action.
    - **Considered:** the exact command alone as the next action, which has no place to say
      where it runs and would hide any other conflict; naming the repair only in the changelog.
    - **Chosen because:** a refusal carries its next step. The planner reports one fact,
      `movable_pin`, and the adoption operation renders it into the sentence it already writes:
      the Mise configuration's conflict is resolved "by running
      `ethos lane repair-paradigm --pin --root <root> --json` in a Work Lane", and any other
      conflict keeps "in <root>".
    - **Applies to:** an older bare pin and an `http:ethos` table of the same or an older
      release. A newer selection, a pin with options, another provenance setting and a
      configuration that does not parse keep the sentence as it was.

## Risks / Trade-offs

- The relock, the projection and the rerun through `mise exec --locked` are named and not
  proven: no test runs Mise or a projection compiler. Whether a relock drops the lock's entries
  of the removed `http:ethos` tool is not verified.
- The order of the projection step relative to the lane's commits is not verified in a Work
  Lane; the first projection of a repository needs its declarations committed first.
- A blocked preview exits zero, as every preview of this command does; a caller that reads only
  the exit status of a preview does not see the block.
- A configuration with CRLF line endings blocks the plan with `carrier_edit_preimage_changed`,
  as it does for any carrier: the plan reads carriers as LF text.
- A pin in a root `mise.toml` reads as no pin, so `--pin` would add a second selection to
  `.config/mise/config.toml`.
- The scenario for adoption's conflict sits under this Change's requirement, because
  `Adoption continuation preserves request meaning` already has an open MODIFIED delta in
  `adopt-lock-directory`.
- The plan that adoption returns gains the field `movable_pin`.
- `src/ethos/repository/paradigm/repair.py` reaches 471 effective lines of 500. A split needs its
  private table remover made public, which renames a pinned entry of the decision-density
  baseline; this Change does not split it.
- A repository that declares a projection file with no relation gets the projection step named,
  and that step then reports `projection_declaration_missing`.
