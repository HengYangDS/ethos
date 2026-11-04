# Proposal

## Why

An Archify explainer draft, `*.archify.md`, carries directive lines such as `@source <id>
title="…" path="src/ethos/…" lines=a:b` and `@meta repo_url="https://github.com/…"`. They are
arguments for the Archify renderer, not prose, but the Vale policy that ETHOS ships reads them as
Markdown text, so a source path or a repository URL fails `Vale.Terms`. architecture-publications
cannot land its guides for this reason: Archify rejects HTML comments, so `<!-- vale off -->` is
unavailable, a file path cannot be reworded, and a repository's own Vale policy runs after the
shipped one and cannot relax it.

## What Changes

- The shipped Vale policy ignores the directive lines of an Archify draft: the lines of a
  `*.archify.md` file that start with `@` and a lowercase directive name. Every other line of the
  draft keeps the full Markdown policy, and other Markdown files are unaffected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement names the text that the shipped Vale policy reads.

## Impact

`.config/checks/vale/vale.ini`, which ETHOS ships to every governed repository, a test in
`tests/unit/adapters/gates/test_prose.py`, and `CHANGELOG.md`.
