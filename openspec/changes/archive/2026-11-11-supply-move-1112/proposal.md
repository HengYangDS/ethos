# Proposal

## Why

The owner asked for every supply chain to move to its newest stable release. ETHOS last moved its
supply on 2026-11-10 (`supply-move-1110`). Against a cutoff of 2026-11-10T18:00:00Z, three Mise
tools, three npm pins, the npm lock and the Python lock have newer stable releases, and so has Mise.

## What Changes

- Mise stays at 2026.10.25. Under Mise 2026.11.6, the CI supply image build's
  `mise install --locked` refused the locked Python 3.14.10 archive for Linux arm64 on its
  checksum, so the move to it waits for its own Change.
- Go moves to 1.27.4, Syft to 1.57.1 and Grype to 0.121.3, in the Mise configuration and its lock.
- npm: `@fission-ai/openspec` moves to 1.17.0, the `minimatch` override to 11.0.6 and `re2js` to
  2.10.0, and the lock-only update moves the transitive packages to their newest releases before
  the cutoff.
- The Python lock moves to the newest releases before the cutoff, and the floors of the moved
  direct dependencies rise to their locked versions. `ty` 0.0.100 renames the rule
  `unresolved-attribute` to `missing-attribute`, so the one ignore comment that names it moves
  to the new name.
- The CI supply image is rebuilt from the moved locks and bound in `.config/ci/pipeline.cue`.
- The Unreleased entry names the moves.

Already newest under the cutoff, and unchanged: Node.js, Python, uv, CUE, actionlint, scc,
gitleaks, Vale and the seven action pins. Node.js 26.13.1, python-build-standalone 20261110 and
Prettier 3.10.0 are stable but younger than the cutoff, so they wait for the next move.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Locked versions change; no requirement changes.

## Impact

`.config/mise/config.toml`, `.config/mise/mise.lock`, `package.json`, `package-lock.json`,
`uv.lock`, `pyproject.toml`, `.config/ci/pipeline.cue` with its generated projection,
`src/ethos/contracts/semantic.py` and `CHANGELOG.md`.
