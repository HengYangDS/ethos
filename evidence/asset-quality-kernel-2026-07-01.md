---
subject: ethos:evidence:asset-quality-kernel
role: evidence
state: active
relations:
  supports: ethos-asset-quality-kernel
---

# Asset Quality Kernel Evidence - 2026-07-01

## Scope

- Added `ethos-quality` as a first-class product package for quality,
  determinism, documentation profile, gate descriptors, and proof policy.
- Updated product package ontology, workspace metadata, OpenSpec families, and
  scaffold family generation to include `ethos-quality`.
- Expanded gate and proof schemas with asset classes, dimensions, execution
  mode, evidence class, trust-bearing classification, adapter identity,
  write/network policy, proof verdict, diagnostics, and proof lattice states.
- Strengthened docs quality with taxonomy state checking, stable-entry visible
  sections, glossary navigation, and nested command example validation.
- Removed reference-adopter instance terminology from provider-neutral
  `ethos-contracts` capability parity records.
- Expanded self-evolution hypotheses with owner, transition, proof refs, review
  refs, decision refs, and retirement conditions.
- Fixed the executed-proof result translation contract so ETHOS JSON
  `ok=false` outputs block proof even when the process exits `0`.
- Tightened proof-run lattice validation in both Python and JSON Schema:
  trust-bearing runs must be `proven`, and `proven` runs must be
  trust-bearing.
- Exposed the full documentation registry `required_gaps` set at the CLI result
  envelope, not only missing front matter.
- Expanded claim promotion targets to cover the complete semantic change
  surface: package metadata, source, schemas, docs, tests, OpenSpec records,
  claim, and dated evidence.
- Reconciled this quality-kernel lane onto the current `candidate/dev` Skills V2
  baseline by keeping live skill activation/schema validation, adding
  `distributions/**` to repository-governance playbook routing, and making the
  `playbooks-v2` gate a trust-bearing governance contract.

## Verification

Commands run from `work/asset-quality-kernel`:

```bash
uv run --group dev pytest tests/unit/test_quality_kernel.py tests/unit/test_docs_registry.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_cli_contracts.py tests/unit/test_self_evolution_ledger.py tests/unit/test_parity_command.py tests/architecture/test_product_boundaries.py -q
uv run --group dev pytest -q
uv run --group dev ruff check .
uv run openspec validate --all --strict --json
uv run --package ethos ethos quality asset-policy --json
uv run --package ethos ethos quality docs --json
uv run --package ethos ethos quality schemas --json
uv run --package ethos ethos quality command-examples --json
uv run --package ethos ethos quality proof-policy --json
uv run --package ethos ethos quality tool-profiles --json
uv run --package ethos ethos playbooks route --changed --json
uv run --package ethos ethos prove --execute --gate playbooks-v2 --json
uv run --group dev pytest tests/unit/test_runner_and_evidence.py tests/unit/test_cli_contracts.py tests/unit/test_schema_validation_and_gates.py tests/unit/test_claims_governance.py -q
uv run --package ethos ethos self audit --mode deep --json
uv run --package ethos ethos report --json
uv run --package ethos ethos prove --json
uv run --package ethos ethos prove --execute --gate self-audit --gate claims --gate docs-registry --gate schemas --gate markdown-structure --gate format-policy --gate asset-determinism --gate schema-contracts --gate proof-policy --json
uv run --package ethos ethos prove --full --execute --json
uv build --all-packages
npm run test:npm
```

Observed results:

- Review-remediation regression tests for runner/evidence, CLI contracts,
  schemas/gates, and claims governance: `112 passed`.
- Full unit and architecture suite: `309 passed`.
- Ruff: all checks passed.
- OpenSpec strict validation: `9` specs passed, `0` failed.
- Documentation quality: `ok=true`, no required gaps, including visible reader
  sections, link/anchor checks, glossary coverage, and wrapped command-example
  validation.
- Schema validation: `ok=true`, no required gaps, `34` schemas; real quality
  profile, quality gate plan, and Skills V2 payloads validate against tracked
  schemas.
- Asset policy: `ok=true`, `9` asset classes.
- Command examples: `ok=true`, no required gaps.
- Proof policy: `ok=true`, `7` proof states.
- Tool profiles: `ok=true`, `10` mature adapter profiles.
- Playbook routing for changed scope: `ok=true`, no unmatched changed paths.
- `playbooks-v2` executed proof: `ok=true`, `state=proven`.
- Deep self-audit: `ok=true`, stage `complete`, no required gaps.
- Product report: `score=15`, `max_score=15`, product gaps `0`, parity pending `0`.
- Dry-run proof: `ok=true`, `state=ready`, no required gaps; planned proof
  runs are not trust-bearing.
- Extended quality-kernel executed proof: `ok=true`, `state=proven`, no
  required gaps, `9` gates.
- Full executed proof: `ok=true`, `state=proven`, no required gaps, `13` gates,
  including unit/architecture tests, build smoke, OpenSpec strict validation,
  and trust-bearing quality gates.
- Local build smoke: all eight workspace packages produced wheel and sdist
  artifacts under `dist/`.
- npm launcher dry-run: `@agentic-workflow/ethos@0.1.0-alpha.1` pack dry-run
  succeeded with `3` tarball files.

## Publication Boundary

No remote publication was performed in this batch. The verification stayed local:
no `git push`, PyPI/TestPyPI publish, npm registry publish, Docker/OCI push,
Homebrew publish, GitHub Action marketplace publish, or GitLab component publish
was executed.

## Traceability Notes

The claim promotion set includes all semantic source files, quality schemas,
workspace/package metadata, lockfile, OpenSpec capability family, current docs,
tests, the claim, and dated evidence needed to reconstruct the quality-kernel
release surface. The build and npm checks are local smoke evidence only; they
do not create durable release artifacts.
