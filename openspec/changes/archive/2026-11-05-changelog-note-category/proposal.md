# Proposal

## Why

The full proof of `e7d95f903` blocked at once on `repository_paradigm_changelog:CHANGELOG.md`.
`beta-1-withdrawal` put its two release notes as plain paragraphs before each entry's first
category heading. The changelog grammar requires every statement inside a category, so it reports
`release_changelog_content_uncategorized` for 0.2.0-beta.2 and 0.2.0-beta.1.

## What Changes

- Both notes move into their entry's `### Changed` category as the first bullet, with the same
  words.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A formatting correction changes no requirement, so `skip_specs: true` applies.

## Impact

`CHANGELOG.md`.
