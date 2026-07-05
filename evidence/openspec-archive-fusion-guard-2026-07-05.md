---
subject: ethos:evidence:openspec-archive-fusion-guard
role: evidence
state: active
relations:
  supports: ethos-openspec-archive-fusion-guard
---

# OpenSpec Archive Fusion Guard Evidence - 2026-07-05

This evidence records the guard that prevents OpenSpec archive closeout from
silently weakening accepted specs.

## Scope

- Added shape-audit detection for removed accepted OpenSpec `WHEN`, `THEN`, and
  `AND` obligation lines in `openspec/specs/**/*.md`.
- Added regression tests for deleted obligations and allowed added obligations.
- Updated product contract and `ethos-repository` spec to require archive fusion
  rather than replacement.
- Added OpenSpec carrier `openspec/changes/ethos-openspec-archive-fusion-guard-20260705`.

## Verification

Commands run from `work/openspec-archive-fusion-guard`:

```bash
uv run --group dev pytest tests/unit/audit/test_modes.py::test_openspec_shape_flags_removed_accepted_spec_obligations tests/unit/audit/test_modes.py::test_openspec_shape_allows_added_or_unchanged_spec_obligations -q
uv run --group dev pytest tests/unit/audit/test_modes.py tests/unit/product/test_openspec_edges.py tests/unit/product/test_openspec_cache.py -q
uv run --group dev ruff check .
uv run --group dev ruff format --check .
uv run --package ethos ethos report --json
uv run --package ethos ethos plan --changed --json
```

Observed results:

- Focused OpenSpec obligation tests: `2 passed`.
- OpenSpec/audit focused suite: `24 passed`.
- Ruff check: all checks passed.
- Ruff format: `188 files already formatted`.
- Report: `ok=true`, `score=16/max_score=16`, `governance_gap_count=0`, `parity_pending_count=0`.
- Plan: `ok=true`, `state=planned`, `required_gaps=[]`.

Full executed proof and OpenSpec lifecycle validation are run after the claim
digest is refreshed and the repository HEAD is finalized.
