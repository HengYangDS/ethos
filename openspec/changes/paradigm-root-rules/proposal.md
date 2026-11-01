# Proposal

## Why

The repository paradigm asks less of a governed repository's root than ETHOS asks of its own, and it
refuses a remote name that Git and both forges use when it is unambiguous.

- The paradigm requires only `AGENTS.md` and `README.md`
  (`src/ethos/contracts/paradigm/paradigm.toml`, `required_documents`). ETHOS's list of release
  files, which adds `CONTRIBUTING.md` and `LICENSE` (`REQUIRED_RELEASE_FILES`,
  `src/ethos/repository/release/configuration.py:24`), is read only by ETHOS's own product audit and
  by `release_policy_report`, which has no production caller. Of the 13 governed repositories on the
  owner's workstation, 7 had no `CONTRIBUTING.md` on 2026-11-01, among them filmkit, which releases
  and publishes to both forges; ETHOS let each prove, land and release.
- The paradigm reports a remote named `origin` even when the repository has one publication peer.
  `git clone` gives the one remote it clones from that name, and both forges' CI clones use it; it
  becomes ambiguous only beside a second remote.

## What Changes

- Every governed repository keeps `AGENTS.md`, `CONTRIBUTING.md` and `README.md` at its root.
- A repository that tags releases keeps its license grant in `LICENSE`, beside the `VERSION` and
  `CHANGELOG.md` it already keeps.
- ETHOS's own release-file list is derived from the paradigm, so one declaration owns what a
  repository root holds.
- The paradigm declares the name a clone gives its remote, Git's default `origin`. A sole
  publication peer may keep it; with two or more peers, each remote takes its peer id and none keeps
  the clone name. No check repeats the name.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-paradigm`: the root documents, the release license grant and the remote names.

## Impact

`src/ethos/contracts/paradigm/paradigm.toml` and its model `declaration.py`,
`src/ethos/repository/paradigm/report.py`, `src/ethos/repository/release/configuration.py`,
`src/ethos/repository/audit.py`, their tests and the `repository-paradigm` specification. **Breaking
for adopters:** a governed repository without `CONTRIBUTING.md`, or a releasing one without
`LICENSE`, gains a paradigm gap when it moves to this release.
