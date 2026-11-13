# Proposal

## Why

On 2026-11-13 batch 3's staged text check refused every ETHOS commit under the installed runtime
with `format_selection_increment_invalid`: the product repository keeps the full format policy,
which no adopter has, and the check read it as a carrier increment. Proofs run from source, so no
gate ran the generated hook under an installed runtime in the product repository, and the defect
shipped. The approved common-base design makes that check an RC item (its Change 10).

## What Changes

- `local-install-smoke` gains one step for the clean development build of the head: in a clone of
  the product repository, a Work Lane selects the delivered runtime, and its `pre-commit` admits a
  conforming staged edit and refuses a staged `.gitignore` that opens with a blank line.
- The local-install receipt records both outcomes; a release or dirty build records the step as
  not qualified, since only the development identity of the accepted head can be selected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: ADDED requirement `The installed hook admits the product repository`.

## Impact

`tools/ci/delivery/acceptance/`, its unit tests and `openspec/specs/quality/spec.md` through this
Change's delta.
