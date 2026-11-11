# Proposal

## Why

The 0.2.0-beta.7 entry's Added list holds one blank line between two single-paragraph items. In
CommonMark that one line makes the whole list loose, so every item renders as a spaced paragraph,
while Prettier keeps the line because it treats the item before it as loose. The repository's
Markdown rule keeps tight list items tight; a separator before the next item belongs only after an
item with more than one block. An audit of the repository's live Markdown found no other such gap.

## What Changes

- The stray blank line leaves the 0.2.0-beta.7 entry's Added list, so the list is tight again.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Only the layout of one historical entry changes; its text does not, so `skip_specs: true`
applies.

## Impact

`CHANGELOG.md`.
