# Runtime Cache Boundary Design

## Boundary

The change separates three physical subjects:

1. `.config/checks/<concern>/` — hand-authored policy and tool-native config.
2. `build/runtime/tool-cache/<tool>/` — ignored runtime caches and working state.
3. `build/evidence/quality/<gate>/` — generated proof evidence before review or
   explicit promotion.

This removes a sidecar ignore file rather than adding a new entity. The pytest
cache remains a pytest-native cache, but its repository location now follows the
same generated artifact topology used by other local/runtime outputs.

## Net Gain

- Makes hidden runtime state visible as runtime state, not configuration.
- Preserves pytest's native root configuration in `pytest.ini`.
- Keeps `.config` declarative and script/cache-free.
- Lets the generated-artifact audit explain `build/runtime/` alongside
  `build/ethos/` and `build/evidence/`.
- Reduces cleanup and merge noise by deleting the `.config/checks/pytest`
  sidecar ignore file.

## Recovery

If `build/runtime/` proves too broad, the artifact topology can narrow the allow
prefix to `build/runtime/tool-cache/` while keeping the same pytest cache path and
without moving configuration policy back into `.config/`.
