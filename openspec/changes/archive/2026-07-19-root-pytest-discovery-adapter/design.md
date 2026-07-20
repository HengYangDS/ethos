## Context

`tools/ci/scripts/run-python-tests.sh` remains the trust-bearing test owner and
passes `.config/checks/pytest/pytest.ini` explicitly. That owner is correct.
The distinct failure mode is discovery outside the owner: bare root pytest and
IDE test runners inspect root-native metadata but do not infer a nested config
file. Their default cache home violates the generated-artifact topology.

## Decision

Use the one supported root discovery adapter already accepted by the quality
audit: `[tool.pytest.ini_options]` with only the semantic `cache_dir`. The
adapter provides a single discovery invariant, while the concern-owned INI
continues to own every behavioral pytest option. The owner script still passes
the INI explicitly, so its proof semantics do not depend on implicit discovery.
The quality audit likewise invokes its public CLI checks through the workspace
runtime, so its projections cannot fail merely because the root project is
non-package metadata.

## Consequences And Boundary

- Bare pytest and IDE discovery write cache under
  `build/runtime/tool-cache/pytest` rather than root `.pytest_cache`.
- Direct discovery does not acquire strict markers, timeout, coverage, JUnit,
  or owner-script evidence semantics; it must not be described as product proof.
- No root `pytest.ini`, forwarding shim, duplicate option, or compatibility
  layer is introduced.
- Regressions assert the exact minimal table, so future root pytest policy
  growth fails closed in review.
