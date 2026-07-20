## Context

`adopter-openspec-lifecycle-20260714` is active with `semantic_scope` freshness. Its promotion targets currently name `packages/ethos/src/ethos/surface/cli/root` and `tests/unit/cli`, so unrelated changes in either directory invalidate the claim. The archived lifecycle Change identifies the actual correction as `planning.py`, `proof.py`, and the adopter lifecycle regressions.

## Goals / Non-Goals

**Goals:**

- Bind freshness to the smallest authoritative behavior surface: both lifecycle command implementations and the exact plan/prove adopter regressions.
- Keep the semantic digest implementation unchanged and fail closed when any selected file changes.
- Refresh only claim evidence/Chronicle truth; do not overstate a new lifecycle proof.

**Non-Goals:**

- No change to OpenSpec lifecycle evaluation, code-correctness gates, Superpowers authority, remote publication, or generic claim semantics.

## Decisions

1. **Use explicit file targets, not directory patterns.** The lifecycle correction is implemented in `planning.py` and `proof.py`; the exact behavioral contract is in `test_adopter_openspec_lifecycle.py` and `test_contracts_proof.py`. These files form the semantic scope. Broad directory targets admit unrelated churn and are not an accurate claim boundary.
2. **Keep `semantic_scope`, not `historical` or `head_bound`.** The claim must stale when its behavior changes. A historical mode would stop currentness checks; a head-bound mode would stale on all unrelated commits.
3. **Test target selection and stale behavior through the public claim reader.** The regression checks the production claim envelope's selected paths and uses the existing semantic digest seam to prove selected behavior drift fails closed.

## Risks / Trade-offs

- **A future lifecycle regression is added outside the explicit list** → review must update the claim scope in the same governed change; the selected paths are visible in `ethos quality claims --json`.
- **A listed test is refactored without behavior change** → it correctly requires an evidence refresh because the declared behavioral regression changed.

## Migration Plan

1. Add RED regression for exact target selection and stale behavior.
2. Update the active claim targets, refresh its semantic digest and Chronicle checksum.
3. Validate strict OpenSpec, claims, lifecycle, and focused proof before committing.

Rollback restores the previous claim envelope; no implementation behavior is changed.
