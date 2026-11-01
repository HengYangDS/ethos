# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.25` lacks five product Changes that the
accepted `dev` carries after this lane:

- `worktree-input-inventory`: a tracked file that a lane deletes without staging the deletion is no
  longer quality input, a focused proof refused only by unselected axes names the full proof, and a
  JavaScript test-scope refusal names its files.
- `paradigm-single-source`: the formatters run on the settings ETHOS ships (GitHub issue #20), and a
  root `package.json` `version` that equals `VERSION` is a checked projection. The owner of
  `architecture-publisher` waits for that projection to publish its npm package from the root.
- `native-outcome-evidence`: a failed or timed-out native command keeps its whole outcome, and an
  expired provider deadline reports `gate_timeout` as unknown (GitHub issues #16 and #19, GitLab
  issue #2).
- `hosted-test-environment`: hosted verification passes again on both peers, and a stuck test writes
  its stacks before its bound ends it.
- `paradigm-root-rules`: every governed repository keeps `CONTRIBUTING.md`, a releasing one keeps
  its `LICENSE`, and the paradigm declares the remote name a clone gives its sole peer. This is
  breaking for four governed repositories, whose owners have the list.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.26`. No lock or test changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.26` entry. It describes every user-visible
  product change since `v0.2.0-alpha.25` and the known advisories in the release's shipped bytes.
- The shipped adopter CI model selects `jdx/mise-action` 5.2.5 (`6612f0ef`), its latest release
  since 2026-10-31, instead of 5.2.4. Each adopter's projected workflow takes it when the adopter
  regenerates its projections.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `CHANGELOG.md` and `.config/ci/verification.cue`. No
lock or supply image change: none of the eight inputs that the supply image hashes changed since
`v0.2.0-alpha.25`, and ETHOS's own workflows do not use `jdx/mise-action`.
