# Proposal

## Why

The owner asked on 2026-11-02 that every supply chain move to its latest stable release
("所有供应链都升级到最新稳定版"). `0.2.0-alpha.28` moved every pin that was behind when it was read,
2026-11-02 22:52. Read again on 2026-11-03 between 00:02 and 00:53, four pins were behind: Mise
2026.10.25, which the host and the adopters' CI already run, and Cyclopts 5.3.3, filelock 4.2.7 and
python-discovery 1.9.1 in the Python lock.

## What Changes

- Mise: `min_version` and the CI bootstrap `version` move to 2026.10.25 together, with the six
  official executable digests that the release's `SHASUMS256.txt` states.
- Python: `uv lock --upgrade` moves Cyclopts to 5.3.3, filelock to 4.2.7 and python-discovery to
  1.9.1; the direct floors of Cyclopts and filelock follow the lock.
- The projection test reads the Mise floor from the Mise configuration instead of repeating its
  version, so the next Mise move changes no test.
- Supply image: rebuilt from this lane by the hosted `supply_image` workflow and bound by digest in
  the CUE owner.
- Unchanged because already latest: every pinned action, uv 0.13.6, npm 12.2.1 and the packages it
  bundles, Node 26.13.0, Vale 3.26.0, gitleaks 8.30.1, CUE 0.17.1, Go 1.27.3, actionlint 1.7.12,
  scc 4.1.0, Syft 1.55.0 and the image base digest. CPython stays at 3.14.10: `cel-expr-python`
  0.1.3 publishes no CPython 3.15 wheel or source distribution.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This refreshes the supply under the existing quality and runtime contracts, so
`skip_specs: true` applies.

## Impact

`.config/mise/config.toml`, `.config/checks/ci-projection/policy.toml`, `pyproject.toml`, `uv.lock`,
`tests/architecture/test_ci_provider_projections.py`, `CHANGELOG.md`, `.config/ci/pipeline.cue` and
the GitLab projection generated from it.
