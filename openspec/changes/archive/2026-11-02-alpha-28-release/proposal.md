# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.27` lacks the product Changes that the
accepted `dev` and this lane carry:

- `pixi-dependency-owners`: a conda package that a repository's Pixi manifest declares owns the
  executable of its package name. The getting-started guidance for Pixi waits for this release.
- `archive-preview-simulation`: `ethos lane archive-change` previews the archive it would apply, so
  an over-long merged requirement blocks the preview instead of the apply.
- `publication-pack-walk`: ETHOS pushes without Git's sparse pack walk, so a batch of renamed
  directories no longer exceeds GitLab's push limit.
- `dead-carriers`: three system contracts and the `svg-format` gate that nothing read are gone.
- `absorbed-proposal-retirement`: an accepted publication names the proposals it absorbed and their
  exact retirement.
- `landing-proof-authority`: landing binds the Change that its admitted proof carries.

The owner asked on 2026-11-02 that every supply chain move to its latest stable release
("所有供应链都升级到最新稳定版"). Read that evening against the registries and release feeds, Vale,
five locked Python packages and npm packages within their declared ranges were behind.

## What Changes

- Supply, each through its owner's native resolver:
  - Mise: Vale 3.26.0, locked for every platform of the lockfile.
  - Python: `uv lock --upgrade` moves anyio to 4.16.0, Authlib to 1.9.2, FastMCP and fastmcp-slim to
    4.1.5 and platformdirs to 4.14.3; the direct floors follow the lock. The quality sample's lock
    has nothing to move.
  - npm: globals 17.14.0 and the minimatch override 11.0.4, then `npm update` moves every package
    within its declared range, 27 of them. Every resolved URL stays on the public registry.
  - Supply image: rebuilt from this lane by the hosted `supply_image` workflow and bound by digest
    in the CUE owner, so GitLab checks the moved locks against an image built from them.
  - Unchanged because already latest: every pinned action, uv 0.13.6, npm 12.2.1, Node 26.13.0 LTS,
    gitleaks 8.30.1, CUE 0.17.1, Go 1.27.3, actionlint 1.7.12, scc 4.1.0, Syft 1.55.0 and the image
    base digest.
  - Not moved: CPython stays at 3.14.10. Python 3.15.2 is the latest release, but
    `cel-expr-python` 0.1.3 publishes no CPython 3.15 wheel and no source distribution, and PyYAML
    6.0.3 publishes only a source distribution for it, so `requires-python` stays `<3.15`.
- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.28`.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.28` entry with its Security notes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release and refreshes its supply under the existing quality and runtime
contracts, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `CHANGELOG.md`, `pyproject.toml`, `uv.lock`,
`package.json`, `package-lock.json`, `.config/mise/config.toml`, `.config/mise/mise.lock`,
`.config/ci/pipeline.cue` and the CI projections generated from it.
