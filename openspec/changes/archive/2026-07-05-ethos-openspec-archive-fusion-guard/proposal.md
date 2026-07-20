## Why

OpenSpec archive closeout is a carrier transition: active deltas are applied to
accepted specs and then archived. A tool-applied `MODIFIED` delta can replace an
accepted requirement and silently delete existing scenario obligations. That is
a small but high-signal governance failure: accepted truth was weakened by a
projection step.

## What Changes

- Add an always-run shape-audit guard that detects removed accepted OpenSpec
  `WHEN`, `THEN`, or `AND` obligation lines in `openspec/specs/**/*.md`.
- Require humans/agents to fuse obligations forward or carry an explicit removal
  decision instead of silent replacement.
- Keep the guard Git-native and repository-local; no new truth store or command
  plane is introduced.

## Capabilities

- `ethos-repository`: subject=openspec-archive-fusion-guard; reuse=extend; change=modify; facet:lifecycle=archive; facet:surface=openspec; facet:authority=source; facet:authority=test; facet:authority=docs; facet:authority=claim; facet:authority=evidence

## Out Of Scope

- No replacement of the official OpenSpec archive command.
- No semantic parser for all Markdown prose.
- No permission to delete accepted obligations without explicit removal carrier.
