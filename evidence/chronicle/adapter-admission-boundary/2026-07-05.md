---
subject: ethos:evidence:adapter-admission-boundary
role: evidence
state: active
relations:
  supports: ethos-adapter-admission-boundary
---

# Adapter Admission Boundary Evidence - 2026-07-05

This evidence records the generic hardening that keeps external frameworks,
provider profiles, hosted surfaces, model/editor hosts, and distribution
launchers from entering ETHOS as implicit truth centers.

## Scope

- Added adapter/profile admission metadata to the coupling registry.
- Schema-governed the admission object in `coupling-audit.schema.json`.
- Added regression coverage for missing admission, wrong truth boundary, and
  draft decision state.
- Updated the product design contract to require admission authority, truth
  boundary, and decision state for adapter/profile bindings.
- Added OpenSpec carrier `openspec/changes/archive/2026-07-05-ethos-adapter-admission-boundary-20260705`.

## Verification

Commands run from `work/vendor-boundary-hardening`:

```bash
uv run --group dev pytest tests/unit/audit/test_coupling.py -q
uv run --package ethos ethos quality coupling-audit --json
uv run --group dev ruff check packages/ethos/src/ethos/repository/policy/coupling.py tests/unit/audit/test_coupling.py
uv run --group dev ruff format --check packages/ethos/src/ethos/repository/policy/coupling.py tests/unit/audit/test_coupling.py
```

Observed results:

- Coupling tests: `17 passed`.
- Coupling audit: `ok=true`, schema validation `ok=true`, `required_gaps=[]`.
- Ruff focused check: all checks passed.
- Ruff focused format: files already formatted.

Additional validation in the same Work Lane:

```bash
uv run --group dev ruff check .
uv run --group dev ruff format --check .
.config/ci/scripts/run-python-tests.sh
uv run --package ethos ethos openspec --lifecycle --json
uv run --package ethos ethos quality claims --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos report --json
uv run --package ethos ethos prove --execute --expect-head $(git rev-parse HEAD) --json
```

Observed results:

- Ruff check: all checks passed.
- Ruff format: `188 files already formatted`.
- Python CI gate: `647 passed`; coverage `95.06%`; required `95%` reached.
- OpenSpec lifecycle: `ok=true`, official validation `10` items passed, `0` failed, `required_gaps=[]`.
- OpenSpec archive: archived as `2026-07-05-ethos-adapter-admission-boundary-20260705` with `specsUpdated=true`.
- Accepted `ethos-repository` spec was manually reconciled to preserve existing coupling-registry constraints while adding adapter admission requirements.
- Claims: `ok=true`, new claim digest trusted, `required_gaps=[]`.
- Schema validation: `ok=true`; coupling-audit schema accepted adapter admission.
- Report: `ok=true`, `score=16/max_score=16`, `governance_gap_count=0`, `parity_pending_count=0`.
- Executed proof on the pre-commit HEAD: `ok=true`, `state=proven`, `gate_count=8`.

The final commit HEAD must run executed proof again before closeout because
tracked evidence and claim digest changes alter HEAD.
