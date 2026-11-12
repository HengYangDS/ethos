# Design

## Context

See the [proposal](proposal.md). The paradigm declares Prettier as the formatter for `.md`, `.yaml`
and `.yml` with `proseWrap = "preserve"` and `printWidth = 100`. `render_source_content` and
`_postimages` in `src/ethos/adapters/gates/formatting.py` produce each authored file's postimage
for the formatting gate and for `ethos lane format`; files that Prettier's native check accepts
keep their bytes. The authored selection already leaves out the archive, evidence and received
paths. `pre-commit` already measures each staged file's code size on its index blob.

Measured on 2026-11-12 with the repository's Prettier configuration:

| Shape                                                     | Prettier                     | CommonMark       |
| --------------------------------------------------------- | ---------------------------- | ---------------- |
| Stray blank line after a single-paragraph item            | kept                         | whole list loose |
| Item with two paragraphs                                  | adds one blank line after it | loose            |
| Paragraph with a nested list or code block, no blank line | kept                         | tight            |

## Goals / Non-Goals

Goals:

- One rule, decidable from the CommonMark structure, with one owner for check, fix and pre-commit.
- Prettier's output stays valid: the rule only removes what Prettier keeps by mistake and adds what
  Prettier itself adds.

Non-Goals:

- Blank lines outside lists, which Prettier already makes canonical: one between document blocks,
  none at the edges, none doubled.
- Historical carriers: archived Changes, evidence, received files and publisher Skills stay as they
  are.

## Decisions

1. The accepted requirement `Text formatting uses the shipped common formatters` said the paradigm
   adds no layout rule and pinned a loose list of one-paragraph items as valid. The owner's request
   of 2026-11-12 replaces that: the MODIFIED requirement keeps the formatters as the owners of every
   other blank line, and the ADDED requirement states the list rule.
2. `repository/paradigm/markdown_spacing.py` parses with markdown-it-py's CommonMark preset, already
   a dependency, and maps each block start inside a list to the blank lines it needs:
   - Inside an item, one before a paragraph that follows another block and one before any block
     that follows a non-paragraph block; none before a block that follows its introducing
     paragraph.
   - Between items, one after a spread item and none after any other.
3. Blank lines inside a blockquote keep their `>` markers; a fenced code block's own lines are never
   separators.
4. The postimage of a Prettier-owned `.md` file is the spacing pass applied to Prettier's output, on
   both the rendered and the native-clean path. The fix command writes it and the check command
   compares with it, so a second pass changes nothing.
5. `pre-commit` applies the same pass to each staged `.md` blob in the authored selection and
   refuses `pre_commit_markdown_spacing:<path>:<line>` at the first violation.
6. Measured before the change, with the rule over every tracked authored Markdown file:
   - ETHOS has 2 violations, both in `docs/reference/configuration.md`, and this Change repairs
     them.
   - DDWG, architecture-publications, aigw-cli, filmkit and both film repositories have none.
   - Three repositories have some, before the authored selection removes their received paths:
     web-ingestion-benchmark 13, alphasim 11, di-effect 360.

## Risks / Trade-offs

- A governed repository with violations fails its formatting gate after it binds the release;
  `ethos lane format --apply` repairs every one, and the release notes say so.
- A writer who wants a loose list for visual space can no longer leave single-paragraph items
  spaced; the rule follows what CommonMark renders, not the source's look.
