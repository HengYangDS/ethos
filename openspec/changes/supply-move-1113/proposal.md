# Proposal

## Why

The owner asked for every supply chain to move to its newest stable release. ETHOS last moved its
supply in `supply-move-1112`, whose cutoff held Node.js 26.13.1 and python-build-standalone
20261110 for the next move. Node.js 26.13.1 is a security release: it fixes High-severity HTTP/2
and TLS issues on the server side and Medium and Low client-side issues.

## What Changes

- Node.js moves from 26.13.0 to 26.13.1 in the Mise configuration and its lock, and the GitLab
  projection follows from the CUE source.
- CPython 3.14.10 moves from the python-build-standalone 20261026 build to 20261110 in the Mise
  lock.
- The Python lock moves to the newest releases before the cutoff: `cyclopts` 5.4.1, `fastmcp` and
  `fastmcp-slim` 4.1.8, `ty` 0.0.101 and `uncalled-for` 0.6.1.
- The CI supply image's base moves from the uv 0.13.6 image to the uv 0.13.7 image that matches
  the uv pin; the image is rebuilt from the moved locks and bound by digest.
- The Unreleased entry names the moves, with a Security line for Node.js.

Already newest under the cutoff, and unchanged: Python, uv, CUE, Go, actionlint, scc, Gitleaks,
Syft, Grype, Vale and the six action pins. Mise stays at 2026.10.25 until the refusal of the locked
Linux arm64 Python archive under Mise 2026.11.6 is understood. Prettier 3.10 changes the layout of
every governed repository's Markdown, so it moves in its own Change with a fleet format scan.
Python 3.15 stays outside `requires-python`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. Locked versions change; no requirement changes.

## Impact

`.config/mise/config.toml`, `.config/mise/mise.lock`, `uv.lock`, `pyproject.toml` where a direct
floor rises, `.config/ci/supply/Dockerfile`, `.config/ci/pipeline.cue` with its generated
projections, and `CHANGELOG.md`.
