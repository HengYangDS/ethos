## Context

See [proposal.md](proposal.md). Since `v0.2.0-alpha.12` (`4cf39e4a8`) the product source changed in
two places: the host link checks (`src/ethos/adapters/gates/` and
`src/ethos/adapters/repo/content/source.py`) and the mise boundary
(`src/ethos/adapters/toolchain/mise.py` and
`src/ethos/adapters/repo/runtime/materialization/native_supply.py`). The other product commits in
that range either refactor without changing behavior or were withdrawn again by `dc301fc3c`. No
OpenSpec Change is active, so the release entry needs a Change of its own to own its paths.

## Goals / Non-Goals

**Goals:**

- One accepted head whose committed version, curated entry and tests name 0.2.0-alpha.13 and
  describe every product change since `v0.2.0-alpha.12`.

**Non-Goals:**

- Beta qualification. Under DR-0015 a beta needs hosted verification on every supported platform
  and the adopter journey from published assets on macOS and Linux; this release is verified from
  its published assets on macOS arm64 only, so it stays an alpha.
- Refreshing locks or tool pins, and changing how releases are built or published.

## Decisions

- Edit the version owner and its projections as exact replacements that refuse a missing or
  unexpected occurrence, as earlier release entries did, so a partial bump cannot be committed.
- Date the entry with the local calendar day on which the tag is created, as earlier entries are.
- Tag only the accepted head, and only after its hosted runs pass on every platform and the release
  build's own dependency audit is clean on that head. A published tag is immutable; a defect found
  afterwards ships in the next prerelease.

## Risks / Trade-offs

- [An advisory is published between the proof and the release build] → Run the release build's
  audit on the exact head immediately before tagging, and do not tag when it is not clean.
- [The tag is created on a later day than the entry's date] → Tag on the landing day. If tagging
  slips, correct the date transparently in a later change; never move or re-create the tag.
