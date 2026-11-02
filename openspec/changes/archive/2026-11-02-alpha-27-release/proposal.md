# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.26` lacks three product Changes that the
accepted `dev` carries after this lane:

- `declared-parameters`: every wait ETHOS applies is a declared parameter with a default, a unit and a
  bound, a governed repository sets its own under `[paradigm.timeout]` (GitLab issue #2), and every
  gate runs within a deadline that its `gate_completed` event records.
- `pipeline-template-ownership`: a runner declaration owns its identities in a hosted template that
  the CI projection declaration names as the source of that Forge's pipeline, so patch admission and
  the semantic closure stop refusing them. An adopter that keeps its hosted templates under
  `.config/ci/` waits for this fix.
- `owned-literals`: the paradigm declares the branch role names and keys the binding files by role,
  and ETHOS builds every carrier path, version file, changelog and branch name from that declaration.

## What Changes

- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.27`. No lock or test changes.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.27` entry. It describes every user-visible
  product change since `v0.2.0-alpha.26` and the known advisories in the release's shipped bytes.
- No pin changes. On 2026-11-02 every pinned action is its latest release (checkout 7.0.1,
  upload-artifact 7.0.2, download-artifact 8.0.2, setup-uv 10.3.3, login-action 4.7.0, mise-action
  5.2.5), and so are uv 0.13.6, npm 12.2.1, Node 26.13.0, CPython 3.14.10 and gitleaks 8.30.1.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json` and `CHANGELOG.md`. No lock or supply image change: none
of the inputs that the supply image hashes changed since `v0.2.0-alpha.26`.
