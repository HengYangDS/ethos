# Proposal

## Why

The locks have fallen behind the newest stable releases that have been public for at least 24
hours:

| Tool or package | Locked  | Newest at least 24 hours old         |
| --------------- | ------- | ------------------------------------ |
| `coverage`      | 7.17.1  | 7.17.2, published 2026-11-04T19:49Z  |
| Syft            | 1.56.0  | 1.57.0, published 2026-11-05T20:46Z  |
| Grype           | 0.121.1 | 0.121.2, published 2026-11-05T21:22Z |

The quality fixture's lock must move with the project lock, because
`tests/architecture/test_quality_fixture_lock.py` requires every package they share to have one
version.

## What Changes

- `uv.lock` and `tests/fixtures/quality-sample/uv.lock` take every release published before the
  24-hour cutoff, using `uv lock --upgrade --exclude-newer=<cutoff>`, then a plain `uv lock`.
- `.config/mise/config.toml` and `.config/mise/mise.lock` take Syft and Grype releases that are at
  least 24 hours old.
- The test that pins the locked Syft version for the Node declaration moves only if a new Syft
  classifies `node.exe`. Syft 1.57.0 still does not, as
  [Syft issue 5533](https://github.com/anchore/syft/issues/5533) records. So the Node
  declaration stays, and the pin moves to the new version after `node.exe` is checked again.
- The CI supply image is rebuilt and bound, because its manifest covers these files.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. A lock move changes no requirement, so `skip_specs: true` applies.

## Impact

The two `uv.lock` files, `.config/mise/`, the Syft version pin test, and the supply image digest in
`.config/ci/pipeline.cue`.
