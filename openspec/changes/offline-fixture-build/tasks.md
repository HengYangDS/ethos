# Tasks

## 1. Offline Fixture Build

- [x] 1.1 Build the `quality-sample` fixture with uv's bundled `uv_build` backend. Done when a regression proves that every tracked fixture project builds offline from an empty uv cache, and the fixture's lock stays current (`test_tracked_fixture_projects_build_offline_from_an_empty_cache`; `uv lock --check`).
- [x] 1.2 Run the tests that build the fixture. Done when the Python evidence and fixture-supply tests pass on the new backend (`tests/unit/adoption/quality/test_python_evidence.py`, `tests/unit/ci/test_ci_bootstrap.py`).

## Workflow follow-up

- Prove the exact head, then archive this Change and prove again.
- Land only after the release owner reports 0.2.0-alpha.14 released, because a closeout before the tag would move `main`.
