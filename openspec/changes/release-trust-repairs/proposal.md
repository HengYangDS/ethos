# Proposal

## Why

A model review of the release diff (`v0.2.0-beta.10..dev`: product, tools and configuration) on
2026-11-15 returned findings against what 0.2.0-beta.11 adds to the release trust path. The tag of
that release is planned for 2026-11-21, and this Change repairs two of the findings before the
release Change. Each reproduces on this Change's base:

- A checksum-class pin is selected without a lock. A transition that follows the accepted pin
  requires the lock entry of the host's platform only outside the checksum class. In that class it
  selects whatever install Mise reports, also when the accepted branch holds no lock at all. 25 of
  the 36 tagged releases are in the class, and the exact pin form reads each of the 36
  (`git tag --list 'v*'`, read through `release_class` and `declared_pin`).
- The shared conformance accepts any superset of an adoption's files. Since `44d0a756a` the check
  of the CLI, SDK and MCP adoption compares the planned files as a superset, so a development build
  that planned the pin, or any build that planned another file, would pass. The brownfield
  conformance of the same commit keeps an exact list.

No tag contains the commit that introduced either (`git tag --contains`), so no release carries
them.

A third finding is real and moves to `release-acceptance`, the row that first calls the explicit
release transition: that transition refuses a version accepted again across the checksum binding
after admission has accepted it, and it has no caller in this release.

One accepted text is wrong, and the delta corrects it: `runtime-activation`,
`Runtime activation follows the accepted pin forward`. Its scenario
`A checksum-class release is pinned` selects for any lock entry without provenance, including one
that records no checksum, and no scenario names the state of a checksum-class pin whose entry is
absent.

## What Changes

- A transition that follows the accepted pin selects a checksum-class release only when the lock
  entry of the host's platform records its checksum. Without the entry or the checksum it keeps
  `CURRENT` and names `runtime_pin_unattested`, and it refuses by that name when nothing is
  selected.
- The shared conformance requires exactly the files an adoption plans: its two bindings, and the
  pin only from a release build.

Not Breaking: no release carries the changed behavior, and no gap code is added.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `runtime-activation`: MODIFIED requirement `Runtime activation follows the accepted pin forward`.

## Impact

`src/ethos/adapters/repo/runtime/pin_selection.py` and `tools/ci/delivery/acceptance/mcp.py`, one
test module for each, `docs/architecture/local-state.md` and two `CHANGELOG.md` entries under
Unreleased, Fixed.

Out of scope: the release transition's finding, which `release-acceptance` decides; comparing an
install with its lock entry, which stays with Mise and the hosted journey; and a state name of its
own for the checksum class.
