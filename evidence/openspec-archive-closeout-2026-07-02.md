---
subject: ethos:evidence:openspec-archive-closeout
claim: ethos-openspec-archive-closeout
date: 2026-07-02
role: evidence
state: active
relations:
  canonical_for: openspec archive closeout evidence
---

# OpenSpec Archive Closeout Evidence

Purpose: record proof and judgment for the OpenSpec archive closeout Work Lane.

## Scope

This lane makes archive health part of ETHOS OpenSpec lifecycle closeout. The
adapter now reports archive closeout gaps for missing archive metadata,
incomplete task checklists, and malformed delta specs, and `ethos land` consumes
those gaps through the existing OpenSpec lifecycle package.

The lane also archives the prior `ethos-campaign-orchestration` and
`ethos-openspec-product-protocol` carriers through the official OpenSpec archive
command, then updates their claims to point at the dated archive paths.

## RED Evidence

Command run from `/Users/yheng/projects/ethos-work-openspec-archive-closeout`:

```text
uv run --group dev pytest -q tests/unit/test_openspec_native_cache.py::test_completed_active_changes_report_blocks_invalid_archives
```

Result: failed because `completed_active_changes_report` returned `ok=true`
when official OpenSpec list was clean but an archived change lacked
`.openspec.yaml` metadata and had an incomplete task checklist.

## GREEN Evidence

Commands run from `/Users/yheng/projects/ethos-work-openspec-archive-closeout`:

```text
uv run --group dev pytest -q tests/unit/test_openspec_native_cache.py
```

Result: `5 passed`.

```text
uv run --group dev ruff check packages/ethos-adapters/src/ethos_adapters/openspec_native.py tests/unit/test_openspec_native_cache.py
```

Result: `All checks passed`.

## Archive Actions

Commands run from the Work Lane:

```text
uv run openspec archive ethos-campaign-orchestration --yes --json
uv run openspec archive ethos-openspec-product-protocol --yes --json
```

Results: official OpenSpec archived the carriers as
`2026-07-01-ethos-campaign-orchestration` and
`2026-07-01-ethos-openspec-product-protocol`, with live specs updated.

The archive closeout gate then reported missing `.openspec.yaml` metadata for
the two newly archived carriers. This lane added metadata for both archives and
for the pre-existing `2026-07-01-ethos-productization-convergence` archive,
which was also missing metadata.

## Product Closeout Checks

Commands run from the Work Lane:

```text
uv run --package ethos ethos openspec --lifecycle --json
```

Result: `ok=true`, `state=clean`, `required_gaps=[]`, with active change
`ethos-openspec-archive-closeout` claim-bound and proposal protocol clean.

```text
uv run --group dev pytest -q
```

Result: `428 passed`.

```text
uv run --group dev ruff check .
```

Result: `All checks passed`.

```text
uv run --package ethos python -c 'import json; from pathlib import Path; from ethos_adapters.openspec_native import completed_active_changes_report; print(json.dumps(completed_active_changes_report(Path.cwd()), indent=2, sort_keys=True))'
```

Result: `ok=true`, `state=clean`, `required_gaps=[]`; archive closeout reported
`14` archives and `0` issues.

```text
uv run openspec validate --all --strict --json
```

Result: `10/10` OpenSpec items passed strict validation.

```text
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos quality schemas --json
```

Result: both commands returned `ok=true`, `state=clean`, and
`required_gaps=[]`.

```text
uv run --package ethos ethos report --json
```

Result: `ok=true`, `state=ready`, score `15/15`, governance gap count `0`,
and parity pending count `0`.

```text
uv run --package ethos ethos prove --execute --expect-head "$(git rev-parse HEAD)" --json
```

Result: `ok=true`, `state=proven`, `required_gaps=[]`, with expected and
current HEAD both `811ced50a9ff25c3d748256a0d6e13e593d95a63`.

```text
uv build --all-packages
```

Result: all workspace source distributions and wheels built successfully.

## Boundaries

- This lane adds archive closeout review; it does not make OpenSpec a public
  ETHOS command plane.
- This lane does not generate adopter OpenSpec scaffolds.
- This lane does not implement hook-based write admission.

Status: see front matter.
