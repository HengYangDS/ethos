## Context

See [proposal.md](proposal.md). The paradigm binds Prettier for Markdown with preserved prose
wrapping. A repository's `fix` and `check` verbs choose which documents Prettier formats, and
ETHOS excludes its official OpenSpec artifacts from those inputs. The repository audit runs in
every prove, land and publish without Node. ETHOS already parses Markdown with markdown-it-py for
its Changelog, document health and template outlines.

## Goals / Non-Goals

**Goals:**

- One blank-line layout for every authored Markdown document in every governed repository,
  whichever formatter inputs a repository declares.
- A repair that adopters run natively, and that never changes what a document says.

**Non-Goals:**

- Formatting other than blank lines, such as tables, emphasis, wrapping or indentation.
- Laying out received evidence or immutable archives.
- Changing which formatter a repository binds or which documents its verbs format.

## Decisions

### Read the structure, not the formatter's bytes

The obligation parses each document with the CommonMark preset and tables, the parser that ETHOS
already uses, and judges only the blank lines between the blocks it finds. Reference definitions
are the only blocks that the parser emits no token for. Lines that no block covers are therefore
runs of definitions. Prettier keeps owning everything else about the text.

### The formatter's layout, tightened once

Every separator rule is what Prettier 3.9.10 writes from canonical input, with one exception.
Prettier keeps a blank line that an author leaves after a one-block list item, and the paradigm
removes it, as the user's rule requires:

- Between document blocks and after front matter, one blank line.
- Between consecutive definitions, none.
- After a formatter-ignore comment, none, because Prettier joins the ignored node to it.
- Between two HTML blocks, at most one.
- After a list item whose blocks touch, none.
- After a list item whose blocks a blank line separates, one blank line. The same applies
  between that item's blocks, except that a paragraph may touch a list that follows it.

Before adopting the rules, the draft repaired every flagged document in the governed
repositories and ran Prettier over the results. All 110 documents that are not verbatim
transcripts kept exactly the blank-line pattern that Prettier writes. A conforming document is
therefore a fixed point of the formatter's blank lines, and the two owners never disagree.

### Quotes, tables, literal and ignored nodes keep their bytes

The obligation does not lay out these nodes:

- Inside a quote, separators are `>` lines, which Prettier lays out.
- Tables have no internal blank lines.
- Fenced code, indented code and HTML blocks are literal.
- The node after `<!-- prettier-ignore -->` is outside the formatter by declaration.

### Repairs change blank lines only and keep the structure

The repair rewrites separator runs and the document's edges; every other line keeps its bytes.
It then compares the original and the result after parsing each again:

- their front matter;
- their reference definitions by label, destination and title;
- their block tokens by type, tag, markup, information and literal content.

Any difference keeps the gap report-only. For example, dropping blank lines before a document's
YAML-like block would turn a thematic break and a heading into front matter.

### One gap per document

A document reports one `markdown-layout` gap. Its repair text names how many separators differ and
the first line, so the gap identity stays stable however many separators a document has.

### Received and immutable documents are exempt

The names obligation already reads documents that Git attributes mark `linguist-vendored` or
`linguist-generated` as received, and archived Changes are immutable. A transcript that a SHA-256
binds is declared received rather than repaired. ethos-introduction-film already declares its
captured sources this way.

### Official OpenSpec artifacts are laid out too

Repository-paradigm task 3.7 keeps official OpenSpec Markdown without a formatter, because
Prettier rewrites emphasis inside the requirement names that the archive matches (commit
`d56b670fc`). The layout changes only blank lines, never a heading or its emphasis, so it keeps
that decision. Their format owner, `official-openspec`, keeps their content. Their blank lines follow the common
layout, and the official parser accepts them: aigw-cli and openai-responses-proxy already validate
laid-out specs strictly. The official archive writes a new spec's `## Purpose` heading directly
followed by its text, and `ethos lane archive-change` formats the specs it writes with the shared
Markdown formatter before its commit. The formatter writes those separators, and delta specs are
already laid out as authored artifacts, so an archive adds no gap.

## Risks / Trade-offs

- [Tightening changes rendering] → A list of one-block items that an author spaced out renders
  with paragraph margins. The user's rule names tight items as the layout, and the repair is a
  reviewed, explicit edit.
- [Adopters meet a new gap at their next rebind] → `ethos lane repair-paradigm --apply` repairs it
  in the same batch. Only WIB, the two films and ddwg guidelines have gaps at their current
  HEADs.
- [A verbatim document is laid out by mistake] → Repairs run only through a reviewed Work Lane
  edit. Evidence that a digest binds is declared received first.

## Migration Plan

Land the obligation, the repair and ETHOS's own laid-out documents together. Each adopter runs
`ethos lane repair-paradigm --apply` in its runtime-rebind batch, after declaring digest-bound
evidence received.

## Open Questions

None.
