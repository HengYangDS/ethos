# Design

## Context

See the [proposal](proposal.md). The audit read every tracked Markdown file with markdown-it and
flagged a blank line that separates an item holding one block, besides nested lists, from the next
item. Archived OpenSpec Changes and retained originals keep their bytes.

## Goals / Non-Goals

Goals: the repository's live Markdown separates list items only where an item has more than one
block.

Non-Goals: a new lint rule. Prettier owns Markdown layout, and other lint rules own non-spacing
checks; the authoring discipline and the tools that write Markdown keep lists tight.

## Decisions

1. Remove the one blank line; Prettier's check still passes on the file, and the list parses tight.

## Risks / Trade-offs

None: the entry's text and every other line stay byte-equal.
