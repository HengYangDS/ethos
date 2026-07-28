# OpenSpec Capability Specs

Each accepted capability directory contains one authoritative `spec.md` with
its current requirements and scenarios. The directory name is the capability
identity; no parallel metadata file participates in identity, routing, gate
selection, or acceptance.

A change that affects multiple capabilities names each one in `proposal.md` and
places changed behavior in the matching delta spec. Gate selection remains in
`system/gates.toml`; change acceptance remains in the active Commitment.
