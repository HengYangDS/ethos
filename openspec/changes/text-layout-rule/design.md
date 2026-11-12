# Design

## Context

See the [proposal](proposal.md). `_selected_files` in `src/ethos/adapters/gates/formatting.py`
keeps only `native-formatter` rows, so `lane format` and the source-format gate never read a
`canonical-text` file. `render_source_content` holds the native dispatch and is pinned at its
decision-density score, so a new owner cannot add a branch there.

Measured on 2026-11-12 with the shipped settings: Prettier turns `\n\na: 1\n\n\n\nb: 2\n\n\n` into
`a: 1\n\nb: 2\n` for YAML, and does the same for JSON and JavaScript; `cue fmt` does the same for
CUE; Taplo is configured with `allowed_blank_lines = 1` and `trailing_newline = true`.

## Goals / Non-Goals

Goals:

- Every authored text format has one named owner of its blank lines, and every owner acts in
  `lane format`, the gates and `pre-commit`.

Non-Goals:

- Trailing whitespace on content lines and other style rules; a `.gitignore` pattern can end in an
  escaped space.
- Files that their generator or an official owner writes: locks, CI projections, OpenSpec specs.

## Decisions

1. `repository/paradigm/text_layout.py` owns `canonical_text`, a pure function: it empties
   whitespace-only lines, drops blank lines at the start and the end, keeps one blank line from
   each run, and ends a non-empty text with one newline.
2. `_selected_files` admits `canonical-text` rows, and `_postimages` renders them with
   `canonical_text` before the native dispatch, so the check, the fix and the gate share one
   postimage and `render_source_content` keeps its score.
3. `pre-commit` checks each staged authored file whose row is `canonical-text` and refuses
   `pre_commit_text_layout:<path>:<line>` at the first line that differs.
4. The configuration reference gets one table: format, owner, blank-line rule, and the commands that
   check and fix it.

## Risks / Trade-offs

- A governed repository's hygiene files with stray blank lines fail its source-format gate after the
  bind; `ethos lane format --apply` repairs them.
