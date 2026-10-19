# Proposal

## Why

On 2026-10-19 the user reported excess and missing blank lines in Changelogs and other Markdown
documents across every governed repository as one global problem. A read-only scan of committed
Markdown at each repository's HEAD found two causes:

- **The formatter keeps authored list spacing.** Prettier 3.9.10 keeps a blank line that an author
  leaves after a list item of one block, and `prettier --check` accepts it. One such line makes
  the `### Changed` list of ETHOS's own Changelog loose.
- **Documents outside a formatter's inputs drift.** The formatter-binding obligation checks a
  formatter's carrier and settings, not the documents it lays out. Three groups are never laid
  out:
  - ETHOS's official OpenSpec artifacts, with 161 missing separators in 11 main specs;
  - most Markdown in ethos-introduction-film;
  - two web-ingestion-benchmark documents.

aigw-cli, openai-responses-proxy, architecture-publisher and architecture-publications have no
such separator. The user's spacing rule already defines the layout:

- one blank line between blocks and after front matter;
- tight one-block list items;
- one separator around multi-paragraph items;
- no edge padding.

## What Changes

- A `markdown-layout` obligation compares each authored Markdown document with the blank lines
  that its parsed CommonMark structure implies. The layout is the formatter's own, plus one
  tightening that the formatter leaves to authors:
  - One blank line separates adjacent blocks and follows front matter.
  - Consecutive reference definitions stay together.
  - No blank line repeats outside literal blocks or pads a document's edges.
  - A one-block list item stays tight with the next item.
  - An item whose blocks a blank line separates keeps one blank line between its blocks and
    before the next item.
- Exempt content keeps its bytes:
  - quotes, tables and literal blocks;
  - the node after a formatter-ignore comment;
  - documents that Git attributes mark received;
  - immutable archived Changes.
- `ethos lane repair-paradigm` repairs the gap deterministically, changing only blank lines. A
  document whose structure would change stays report-only.
- Main specs that the official archive writes need no new step: `ethos lane archive-change`
  already formats them with the shared Markdown formatter, which writes their separators.
- ETHOS lays out its own documents. Its official OpenSpec artifacts keep their content owner.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: authored Markdown follows the layout of its parsed structure, and a
  formatter's ownership boundary no longer exempts a document from it.

## Impact

This Change touches:

- the paradigm report and repair;
- their regressions;
- DR-0012 and the changelog;
- the blank lines of 13 ETHOS documents.

Adopters conform when they rebind to a runtime that carries the obligation, and
`ethos lane repair-paradigm --apply` lays out their documents. Evidence that a digest binds is
declared received in `.gitattributes`, as ethos-introduction-film already does for its captured
sources.
