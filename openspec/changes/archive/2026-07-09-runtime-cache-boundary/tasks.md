# Tasks

- [x] Move pytest runtime cache from `.config/checks/pytest/.pytest_cache` to
  `build/runtime/tool-cache/pytest`.
- [x] Remove the obsolete `.config/checks/pytest/.gitignore` sidecar.
- [x] Extend generated-artifact topology to admit `build/runtime/` as ignored
  runtime/tool-cache state.
- [x] Update product contract, local-state docs, generated-artifact docs,
  DR-0001, and OpenSpec quality requirements.
- [x] Add focused tests preventing pytest cache regression into `.config/`.
- [x] Run focused tests, lint/format, OpenSpec lifecycle, and generated-artifact
  quality checks.
- [x] Run full local CI and HEAD-bound proof before land.
