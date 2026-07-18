# Tasks

- [x] Move Ruff policy from root `ruff.toml` into `.config/checks/ruff/ruff.toml`.
- [x] Move pytest configuration from root `pytest.ini` into
  `.config/checks/pytest/pytest.ini`.
- [x] Update Python lint and test owner scripts to pass explicit config paths.
- [x] Update system tool catalog, format selection, product contract, release docs,
  contribution docs, and active terminal design references.
- [x] Update adopter scaffold CI projections to use ETHOS/OpenSpec command-plane
  checks rather than product-repository owner scripts.
- [x] Add tests that reject root Ruff/Pytest config regression and stale `ethos self
  audit` examples.
- [x] Run focused tests, Python lint/format ratchet, and config lint.
- [x] Admit documented `tools/ci/scripts/*.sh` owner-script examples without allowing arbitrary `tools/**` command roots.
