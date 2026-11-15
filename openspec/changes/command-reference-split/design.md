# Design

## Context

`docs/reference/command-plane.md` reads 497 nonblank lines at the base, in fifteen sections after
ten opening lines. Counted the same way per section, with `grep -c '[^[:space:]]'` over each
section's lines:

| Section                                      | Lines | Section                         | Lines |
| -------------------------------------------- | ----- | ------------------------------- | ----- |
| Workflow And Transport Roots                 | 57    | Result Envelope                 | 42    |
| Native CI Projection                         | 20    | Proof Depth                     | 11    |
| Shared SDK Operations                        | 22    | Hidden Operational Roots        | 3     |
| Retained Candidate Materialization           | 15    | OpenSpec Ownership              | 25    |
| Runtime Selection and Recovery               | 48    | Exact Ref Observation For CI    | 15    |
| Accepted Release Selection                   | 46    | Standard And Fast Verification  | 66    |
| Native Merge Continuation                    | 41    | Assurance And Evidence Boundary | 8     |
| Commit Integrity And Accepted History Repair | 68    |                                 |       |

Four facts constrain the cut:

- `repository_context` in `src/ethos/repository/context.py` names four of its sections as the
  `commands` source of agent guidance: `Workflow And Transport Roots`,
  `Runtime Selection and Recovery`, `Proof Depth` and `Assurance And Evidence Boundary`.
- `test_command_plane_documentation_names_every_registered_root` requires the page to name each of
  the eleven registered roots; all eleven are named in `Workflow And Transport Roots`.
- Three Changes prepared for the same batch edit `Workflow And Transport Roots`,
  `Commit Integrity And Accepted History Repair` and `Result Envelope`.
- An installation carries the page: `pyproject.toml` names it for the wheel and the source archive.

At the base and outside the archive, five links to the page carry an anchor
(`git grep -o 'command-plane.md#[a-z0-9-]*' -- ':!openspec/changes/archive'`):
`commit-integrity-and-accepted-history-repair`, `standard-and-fast-verification`,
`authorized-temporary-hook-bypass`, `routine-scoped-execution` and `native-merge-continuation`.
The same command over the archive prints nothing.

## Goals / Non-Goals

Goals:

- The command reference reads 380 nonblank lines or fewer, and every page under `docs/reference/`
  stays under 500.
- A moved section keeps every byte of its text and its anchor.
- Every link resolves, in the source tree and in an installation.
- The repository's document bound is the paradigm's default again.

Non-Goals:

- Rewriting a sentence of the page.
- Moving verification, runtime selection or commit integrity, which the first and third facts
  pin.
- Changing `repository_context` or any other product code.
- A requirement on the anchors of carried pages.

## Decisions

1. **Two reader questions leave the page: integration and release, and CI.**
   - **Rests on:** the section counts and the constraints above. The page answers five questions:
     which command runs and what its result says; how a change is verified (`Proof Depth` and
     `Standard And Fast Verification`); how the runtime and commit trust are selected and repaired
     (`Runtime Selection and Recovery` and `Commit Integrity And Accepted History Repair`); how
     source moves between a lane, the candidate and a release; and what CI declares and runs.
   - **Considered:** (a) a page for each of the five questions leaves 167 lines in the command
     reference, before pointers, beside pages of 77, 116, 102 and 35. It changes
     `repository_context`, moves every anchor that a tracked link names, and breaks the edits of
     the three prepared Changes. (b) Moving the unpinned sections of the `lane` and `hook` roots
     into `operational-roots.md`, as the earlier split that created that page did, leaves 406
     lines in the command reference and 228 in that page, before pointers. It misses the goal,
     and its axis is the command's root, not the reader's question. (c) Moving integration and
     release alone leaves 395, before pointers, and misses the goal.
   - **Chosen because:** these two questions are the ones whose every section is free of a pin.
     The command reference reads 373 lines, `integration-and-release.md` 113 and
     `ci-operations.md` 48. The trade-off accepted: the command reference still answers three
     questions, not one.
   - **Applies to:** `Native Merge Continuation`, `Retained Candidate Materialization` and
     `Accepted Release Selection`, in the order lane, candidate, release; and
     `Native CI Projection` and `Exact Ref Observation For CI`. It does not cover the three
     pinned questions, which a later split may move once their pins are gone.
2. **Both new pages are carried by an installation.**
   - **Rests on:** `test_installed_navigation_preserves_required_links_without_source_checkout` in
     `tests/unit/repository/test_context.py`, which fails with the pointers unresolved while the
     pages are outside the package declaration; the Docs Registry's portability boundary, which
     forbids labelling a required method optional; and the declaration's five readers
     (`git grep -n 'force-include\|only-include' -- tests src tools`), which all derive from
     `pyproject.toml` and pin no list: two in that module, two in
     `tests/unit/release/test_version_identity.py` and the delivery acceptance in
     `tools/ci/delivery/acceptance/effect.py`.
   - **Considered:** a `source-only` title on the five pointers. It changes no packaging, and an
     installation then loses the text on release selection, merge continuation and the CI
     declaration that it carried before.
   - **Chosen because:** a repository that releases or declares CI through an installed ETHOS
     reads these sections from the installation. The trade-off accepted: four lines of
     `pyproject.toml` and two more documents in the wheel and the source archive.
   - **Applies to:** the wheel's `force-include` and the source archive's `only-include`.
3. **Each moved heading keeps one pointer in the command reference.**
   - **Rests on:** the page's own form for `Hidden Operational Roots`, a heading with a pointer
     since that section moved; the anchor counts above; and the fact that links from outside this
     repository cannot be counted here.
   - **Considered:** no pointers, which leaves 360 lines: an old anchor then opens the top of the
     page, where nothing names the new place, and the reference that lists the commands no longer
     names the six command forms of the moved sections. One routing paragraph in the opening
     names them in fewer lines and resolves no anchor.
   - **Chosen because:** a release publishes the anchors of a carried page, and a reader who holds
     one lands on the line that names the section's new place and its command. The trade-off
     accepted: 13 lines and five headings without a body.
   - **Applies to:** the five moved headings. A heading that is removed, not moved, keeps none.
4. **The bound returns by removing the override.**
   - **Rests on:** the default of 500 for `document_nonblank_lines` in
     `src/ethos/contracts/paradigm/paradigm.toml`, and the documentation registry run on a
     registered probe document: with the override it accepts 501 nonblank lines; without the key
     it reports `docs_length_exceeded` for 501 and no gap for 500.
   - **Considered:** declaring `document_nonblank_lines = 500`, which restates the default and
     keeps a table to maintain.
   - **Chosen because:** a repository keeps every default unless it declares its own value, and
     the recorded reason for the higher value ends with the split.
   - **Applies to:** the `[paradigm.size]` table, its reason and its comment in
     `.ethos/rules.toml`.
5. **The new pages declare that they are part of the command reference.**
   - **Rests on:** the registry's relation check, which resolves a `part_of` target to a file, and
     the design-integrity check's list of required projections, which names the command reference
     and neither new page.
   - **Considered:** a `projects` relation to a section of the Product Design Contract, as
     `operational-roots.md` declares. It states a derivation that the moved text never declared.
   - **Chosen because:** the moved sections were the command reference's text and stay its
     subject; containment is the relation that is known to hold.
   - **Applies to:** the front matter of the two new pages.

## Risks / Trade-offs

- The command reference stays the largest page under `docs/reference/`, with 127 lines free. Its
  three remaining questions grow with the product surface.
- Five headings of the command reference hold only a pointer. A reader who scans the page for
  release selection opens one more page.
- A link from outside this repository to a moved anchor still opens the command reference, at the
  pointer and not at the text.
- The integration page orders its sections lane, candidate, release; the command reference had
  them candidate, release, lane.
