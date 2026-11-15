# Proposal

## Why

A governed repository that retires its pre-commit suite for the ETHOS commit hook loses two
checks, reported by a repository's session on 2026-11-15. The hook covers secrets, Python format,
Markdown list spacing, text layout, the line ceiling and package docstrings. It does not cover:

- merge-conflict markers in staged text that is not Python;
- a byte ceiling for an added file.

No gate covers them either.

## What Changes

- Both enter as reporting obligations: they report for one release before they refuse.
- Each ships with the repair that its report names.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The staged checks of the commit hook. Both are new refusals, so the law freeze does not admit
them before 0.2.0, and they follow the rule row's order.

Owner: the release lead. Next action: size them with the first reports after the rule row. Read
again: after 0.2.0.
