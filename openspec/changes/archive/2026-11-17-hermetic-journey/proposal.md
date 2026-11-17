# Proposal

## Why

The release journey decides whether a published prerelease may advance, and its verdict should
depend on the release alone. Today its children see more than that. The journey hands most of them
a reduced copy of the host's environment: the host's home and temporary directory, and a path made
of whole directories, so every executable that lives beside Git is in reach. The children that
inherit instead, the forge's client and the Git commands that build the fixture adopters, see the
whole environment of the runner, its forge token included. Network use is spread over the journey:
each predecessor is locked and installed from the forge between the upgrade steps.

The archived `rc-plan` design gives the remedy in appendix B.5 and orders it as Change 2 of
appendix B.8, after `github-pin`, which landed in 0.2.0-beta.11. The archived `rc-scope-plan`
design places it in the batch of 2026-11-28. The release rehearsal, the rollback after repair and
the journey's hosts all follow this row, and DR-0029 waits for its measured tools size before the
committee decides whether the rehearsal stays in the gate.

The draft `gate-environment` Change lists five measured cases of a verdict that moved with
something outside its subject. For the journey this Change closes two: the launching shell, since
no variable of it reaches a child, and the host's package cache, since a child's home is new. It
narrows a third, the launcher's path: a child reaches only the declared executables and Mise is
bound by digest, but which Git, signing tool and forge client the links name still follows that
path. Ignored files and the holder stay with that row, as do all five cases for a proof's gates.

## What Changes

- One owner gives every child of the journey a fresh environment: a new home and temporary
  directory, Git without system or global configuration, system attributes or templates, and a
  path that holds one link for each declared executable. No other variable of the host reaches a
  child; the three that say where the host's tool supply is are in acquisition's process only
  while it prepares Mise.
- The journey runs in two stages. Acquisition is the only stage that reaches the network: it
  verifies each release, proves its exact GitHub pin and writes a manifest of the archives it
  verified. Qualification reads the manifest alone, checks its environment before its first
  child, hashes each archive again before Mise installs it offline, and runs every journey step.
- The journey runs the Mise executable whose digest the repository binds, never one that the host
  installed.
- The receipt gains `venue`.

Not breaking for a published release or for an adopter: the journey is the repository's own
release tooling. A host that runs it now needs the forge's client and a downloader on its path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `distribution`: two added requirements, for the environment owner and for the two stages, and
  the requirement `A hosted journey qualifies each published prerelease`, which now says which
  stage installs through the pin and which install the steps run on.

## Impact

`tools/ci/delivery/acceptance/host_environment.py`, `tools/ci/delivery/acceptance/journey.py`,
the new `tools/ci/delivery/acceptance/acquisition.py`, `tools/ci/delivery/mise_tool.py`, the
journey's unit tests, `tests/fixtures/decision-density-baseline.json`,
`openspec/specs/distribution/spec.md` and `CHANGELOG.md`. No product module and no hosted
workflow changes.

Out of scope, as the plan says: counting a venue toward qualification, signed local receipts, and
Windows beyond the Git variables.
