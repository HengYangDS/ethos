# Proposal

## Why

Adopters install only published releases, and `v0.2.0-alpha.28` lacks the product Changes that the
accepted `dev` and this lane carry:

- `supply-catch-up`: Mise 2026.10.25 with its official executable digests, Cyclopts 5.3.3,
  filelock 4.2.7 and python-discovery 1.9.1.
- `hosted-once`: a GitHub push to `main` runs only the commit policy job.
- `ci-emulation-retirement`: the optional local CI emulation is gone.
- `ruff-docstrings`: the managed Ruff policy selects `DOC102`, and ETHOS's own docstring checker is
  gone.
- `release-attestation`: the release run attests its archives and wheels.
- `mise-action-5-2-6`: the shipped adopter CI model pins `jdx/mise-action` 5.2.6.
- `readiness-before-admission`: a full executing proof runs its readiness gates before it waits for
  its proof slot and host load.
- `change-root-files`, `tracked-deletion-admission`, `packed-ref-retirement` and
  `staged-format-shipped-settings`: four admission fixes that Codex reproduced in governed
  repositories on 11-03.
- `release-journey`: each release run qualifies its published prerelease on the adopter journey
  on macOS and Linux; this release is the first that it qualifies.
- `superseded-proposal-runs` and `capture-timeout-handshake`: a newer push of a proposal ref
  cancels the hosted run of its earlier push, and a process capture test no longer races its
  timeout.
- `closeout-environment-gap`: admission names a missing repository runtime instead of a policy
  mismatch.
- `host-conformance-timing`, `ci-uv-version-derivation` and `nox-session-output`: hosted timing
  evidence, one owner for the hosted uv version and bounded Nox session output.
- `readiness-only-proof-admission`: a full proof that plans only readiness gates no longer waits
  for its proof slot and host load.
- `formatter-conflict-fix-mode`: the conflict tests of `lane format` also run the authorized fix,
  which must refuse a conflicting formatter increment before any write (GitHub issue 20).
- `archify-directive-lines`: the shipped Vale policy ignores the directive lines of an Archify
  draft, which architecture-publications needs to land its guides.
- `decision-citation`: a Change archives only after it cites every decision record that names it.
- `identity-forward-check`: module layout refuses a product function that only forwards its
  parameters.
- `windows-arm-accepted-runs`: a proposal run leaves the emulated Windows on Arm pair to `dev`'s
  run of the landed commit, which shortens every landing by about 20 minutes.
- `windows-bootstrap-retry`: the hosted Mise bootstrap waits out a Windows file hold instead of
  failing the job, as `dev`'s Windows on Arm job did in GitHub run 41728732273.

The owner asked on 2026-11-02 that every supply chain move to its latest stable release, and on
11-03 that this release wait for uv 0.13.7, which clears Mise's 24-hour age at 10:45 on 11-04.

## What Changes

- Supply, each through its owner's native resolver:
  - Mise: uv 0.13.7 and Syft 1.56.0, locked for every platform of the lockfile.
  - Python: `uv lock --upgrade`, with the direct floors of fastmcp, ty and uv raised to the locked
    4.1.6, 0.0.96 and 0.13.7, and the quality fixture's lock takes the root lock's version of
    every package they share.
  - npm: already latest within its declared ranges; every resolved URL stays on the public
    registry.
  - Supply image: rebuilt from this lane by the hosted `supply_image` workflow and bound by digest
    in the CUE owner.
  - Not moved: CPython stays on the 3.14 line; the owner has no plan to support Python 3.15, so
    `requires-python` stays `<3.15`.
- `VERSION` and `distributions/npm/package.json` move to `0.2.0-alpha.29`.
- The `[Unreleased]` notes become a curated `0.2.0-alpha.29` entry with its Security notes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This prepares a release and refreshes its supply under the existing quality and runtime
contracts, so `skip_specs: true` applies.

## Impact

`VERSION`, `distributions/npm/package.json`, `CHANGELOG.md`, `pyproject.toml`, `uv.lock`,
`tests/fixtures/quality-sample/uv.lock`, `.config/mise/config.toml`, `.config/mise/mise.lock`,
`.config/ci/pipeline.cue` and the CI projections generated from it.
