# Design

## Context

See the [proposal](proposal.md). `formation_plan` writes `README.md`, `AGENTS.md`, `VERSION` and
`CHANGELOG.md` into a temporary candidate after the adoption binding, then `compose_starter`
inventories the candidate as the foundation and, for `python-library`, runs uv and keeps the new
paths as starter outputs. The candidate is not a Git repository until `_prepare_history` runs
`git init` at apply. `repository_paradigm_report` needs the tracked paths and Git's `text` and
`eol` attributes; without them it reports a `line-ending` gap that no repair covers.
`paradigm_repair_plan` reads files and needs no Git. Review 1 of the N2 design (2026-11-12) found
these constraints.

## Goals / Non-Goals

Goals:

- The `foundation` starter's initial commit has no paradigm gap.
- The paradigm owns the content it can repair; formation authors only what no repair writes.

Non-Goals:

- `python-library` conformance (its lock, version projection and tests), a later Change.
- A tool pin in the starter's mise configuration: C3 writes the ETHOS pin and its lock.
- Status routing and the `repair-paradigm` hint for existing repositories.

## Decisions

1. Before the inventory, formation writes `CONTRIBUTING.md` (routes to `ethos status` and `next`)
   and `.config/mise/config.toml` (`locked = true`; `bootstrap` runs `mise install --locked`,
   `check` runs `ethos lane format --check --json`, which needs no lane, and `fix` runs
   `ethos lane format --apply --authorize --json` in a Work Lane with `--expect-head`).
2. It then reports the candidate's gaps, takes `paradigm_repair_plan`'s edits and writes their text
   with LF, so `.gitattributes`, `.editorconfig` and the OpenSpec common rules come from the
   paradigm. These are foundation files, which a generator cannot overwrite.
3. After `compose_starter`, formation initializes the candidate with the same `git init` arguments
   as `_prepare_history`, so apply's second initialization changes nothing, reads Git's line endings
   for the inventory, and computes the report. For `foundation` any gap refuses
   `formation_starter_paradigm_gap` with the gaps as detail; for `python-library` the preview lists
   them as `paradigm_gaps`.
4. Tests: the formed commit's report is empty; the preview's planned files include the new carriers;
   a composition with a gap refuses before any target exists.

## Risks / Trade-offs

- A later paradigm rule that the starter does not meet makes formation refuse until the starter is
  fixed. The paradigm and formation ship in one package, so the refusal names a product defect.
- The candidate's `.git` exists during preview; the temporary directory is removed with it.
