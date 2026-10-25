# Tasks

## 1. Offline Fixture Build

- [x] 1.1 Build the `quality-sample` fixture with uv's bundled `uv_build` backend. Done when a regression proves that every tracked fixture project builds offline from an empty uv cache, and the fixture's lock stays current (`test_tracked_fixture_projects_build_offline_from_an_empty_cache`; `uv lock --check`).
- [x] 1.2 Run the tests that build the fixture. Done when the Python evidence and fixture-supply tests pass on the new backend (`tests/unit/adoption/quality/test_python_evidence.py`, `tests/unit/ci/test_ci_bootstrap.py`).

## 2. Trust Regressions on Hosted Runners

- [x] 2.1 Make the three trust regressions that need an untrusted configuration hide CI detection and require native mise to report the root untrusted. Done when they pass with and without `CI=true`, and when an unhidden marker fails the precondition by name (`tests/support/mise_host.py`; the three regressions pass with and without `CI=true`).
- [ ] 2.2 Date the 0.2.0-alpha.14 entry 2026-10-26, the day its tag is created. Done when the changelog validates with 0.2.0-alpha.14 as its release target.

## Workflow follow-up

- Prove the exact head, then archive this Change and prove again.
- Land before the 0.2.0-alpha.14 tag, as the release owner asked, so that the tagged head passes its hosted verification.
