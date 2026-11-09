# Proposal

## Why

The 24-hour release age admits newer stable releases than the locks hold. Under the cutoff
2026-11-08T14:56:12Z the project lock moves 16 packages, among them Cyclopts 5.4.0, Pydantic
2.14.3, ruff 0.17.4, ty 0.0.99 and cachetools 8.0.0, and the quality fixture's lock moves ruff
0.17.4. The npm pins lag `@fission-ai/openspec` 1.16.1, `allure` 3.33.0, and the `glob` 14.0.4
and `minimatch` 11.0.5 overrides. `allure` 3.33.0's `@allurereport/web-commons` asks
`dompurify ^3.4.17`, so the override that `native-supply-and-configuration` added for 3.4.16 no
longer has a reason. Mise reports no tool newer within its ranges; Python 3.15 lies outside the
project's `requires-python`.

## What Changes

- Both `uv.lock` files move to the newest releases published before the 24-hour cutoff.
- `package.json` pins `@fission-ai/openspec` 1.16.1 and `allure` 3.33.0, and the `glob` and
  `minimatch` overrides 14.0.4 and 11.0.5; the `@allurereport/web-commons` `dompurify` override is
  removed; `package-lock.json` is regenerated under the same cutoff.
- The direct dependency floors in `pyproject.toml` follow the moved locks.
- The CI supply image is rebuilt from the moved files and bound in `.config/ci/pipeline.cue`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- `uv.lock`, `tests/fixtures/quality-sample/uv.lock`, `pyproject.toml`, `package.json`,
  `package-lock.json`, `.config/ci/pipeline.cue` and `.gitlab-ci.yml`.
- A newer ruff or ty may report new findings; they are fixed in this Change.
