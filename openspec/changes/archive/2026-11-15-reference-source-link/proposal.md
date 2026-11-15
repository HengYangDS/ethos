# Proposal

## Why

The command reference is one of the pages that an installation carries. On 2026-11-15 its runtime
selection section gained a link to the local-state architecture page, which an installation does
not carry. The repository's own rule is that such a link is labelled `source-only` and names the
source in its text; the test of installed navigation refused the unlabelled link. The hosted run
of the proposal ref found it before the workstation's proof did, because the pre-check selects
tests by the Python modules a change touches and this change touched a document.

## What Changes

- The link is labelled `source-only` and its text names the ETHOS source.

Not breaking: one link's label and text change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No requirement changes, so `skip_specs: true` applies.

## Impact

`docs/reference/command-plane.md`.
