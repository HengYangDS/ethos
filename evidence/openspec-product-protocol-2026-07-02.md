---
subject: ethos:evidence:openspec-product-protocol
claim: ethos-openspec-product-protocol
date: 2026-07-02
role: evidence
state: active
relations:
  canonical_for: openspec product protocol evidence
---

# OpenSpec Product Protocol Evidence

Purpose: record proof and judgment for the OpenSpec product protocol Work Lane.

## Scope

This lane productizes the OpenSpec proposal protocol in the ETHOS lifecycle
adapter. `ethos openspec --lifecycle --json` now checks active proposal
capability entries for live capability routing, capability profile presence,
required metadata, valid reuse/change vocabulary, and out-of-scope boundaries.

The lane also updates the terminal productization campaign manifest so the
previous `campaign-orchestration` step is recorded as closed and retired at
HEAD `45ae8ec8f2b98218b4637122fa3d82974d1874c8`, while this
`openspec-product-protocol` step becomes active.

## RED Evidence

Command run from `/Users/yheng/projects/ethos-work-openspec-product-protocol`:

```text
uv run --group dev pytest -q tests/unit/test_openspec_native_cache.py::test_openspec_lifecycle_requires_product_protocol_metadata
```

Result: failed because `openspec_governance_report(..., lifecycle=True)`
returned `ok=true` for a proposal with an unknown capability, missing
capability profile, missing facets, invalid reuse stance, and no Out Of Scope
section.

## GREEN Evidence

Commands run from `/Users/yheng/projects/ethos-work-openspec-product-protocol`:

```text
uv run --group dev pytest -q tests/unit/test_openspec_native_cache.py
```

Result: `4 passed`.

```text
uv run --group dev ruff check packages/ethos-adapters/src/ethos_adapters/openspec_native.py tests/unit/test_openspec_native_cache.py
```

Result: `All checks passed`.

```text
uv run openspec validate ethos-openspec-product-protocol --strict --json
```

Result: `1/1` OpenSpec change passed strict validation.

## Full Verification

Commands run from `/Users/yheng/projects/ethos-work-openspec-product-protocol`:

```text
uv run --group dev pytest -q
```

Result: `422 passed in 105.35s`.

```text
uv run --group dev ruff check .
```

Result: `All checks passed`.

```text
uv run --package ethos ethos openspec --lifecycle --json
```

Result: `ok=true`, `state=clean`, `required_gaps=[]`.

```text
uv run openspec validate --all --strict --json
```

Result: `11/11` OpenSpec items passed strict validation.

```text
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos prove --execute --json
uv run --package ethos ethos report --json
uv build --all-packages
```

Results: schemas clean, claims clean, proof `state=proven` with five gates,
report `15/15`, and all workspace packages built successfully.

## Parity Evidence Refresh

After committing this lane, tracked parity evidence needed to bind to the new
product HEAD. The Work Lane refreshed both tracked evidence files through the
ETHOS command plane:

```text
uv run --package ethos ethos parity shadow --adopter generic --target /Users/yheng/projects/ethos-work-openspec-product-protocol --execute --write-evidence --json
uv run --package ethos ethos parity shadow --adopter alphasim-dmgr --target /Users/yheng/projects/alphasim-dmgr-fix-b3 --execute --write-evidence --json
```

Result: both returned `ok=true`, `state=matched`, `required_gaps=[]`.

## Boundaries

- This lane enforces OpenSpec proposal protocol metadata. It does not archive
  active OpenSpec changes.
- This lane does not generate adopter OpenSpec scaffolds.
- OpenSpec remains a mandatory governance dependency behind `ethos ...`; it
  does not become a second public command plane.

Status: see front matter.

See also: [OpenSpec Governance](../governance/openspec-governance.md), [Terminal Governance Product Design](../architecture/terminal-governance-product-design.md), and [Command Plane](../reference/command-plane.md).
