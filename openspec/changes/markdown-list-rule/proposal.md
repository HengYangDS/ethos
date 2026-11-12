# Proposal

## Why

On 2026-11-12 the owner asked that the blank-line rules for ETHOS and every governed repository be
defined clearly and enforced strictly, above all inside list items. No gate enforces them today.
Prettier, the paradigm's Markdown formatter, adds a missing blank line after a list item that holds
two paragraphs, but it keeps a stray blank line after a single-paragraph item and a blank line
between a paragraph and the code block or list it introduces. In CommonMark one such line makes the
whole list loose, so every item renders as a spaced paragraph. Measured on 2026-11-12 with the
repository's own Prettier configuration: a tight list with one stray blank line passes
`prettier --check` unchanged. The rule existed only in prose: the `markdown-list-spacing` Change of
2026-11-11 made a lint rule a non-goal, and the 0.2.0-beta.7 entry's stray line reached `dev`.

## What Changes

- The paradigm states one blank-line rule for list items:
  - Inside an item, a paragraph that follows another block is separated by one blank line.
  - A list, code block, quote or other block follows the paragraph that introduces it with no blank
    line.
  - A block that follows a non-paragraph block is separated by one blank line.
  - An item that holds such a separator is spread, and one blank line follows it before the next
    item; every other item is followed directly by the next one.
- ETHOS's Markdown format applies the rule after Prettier, so `ethos lane format --check` and the
  proof's formatting gate refuse a violation, and `ethos lane format --apply` repairs it.
- `pre-commit` refuses a staged Markdown file that breaks the rule, with its path and line.
- The existing test that pinned a loose list of one-paragraph items now pins its repair.
- The two violations in ETHOS's own documentation are repaired, and the configuration reference
  names the rule's owner.
- The Unreleased section of `CHANGELOG.md` gains a Changed line.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: MODIFIED `Text formatting uses the shipped common formatters`, which said
  the paradigm adds no layout rule of its own and kept a loose list of one-paragraph items; ADDED
  `Markdown list items have one blank-line rule`.

## Impact

A new pure module in `src/ethos/repository/paradigm/`, the formatting gate in
`src/ethos/adapters/gates/formatting.py`, the pre-commit hook, `docs/reference/configuration.md`,
their tests and `CHANGELOG.md`. A governed repository with violations fails its formatting gate
until `ethos lane format --apply` repairs them in a Work Lane.
