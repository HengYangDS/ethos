# Design: Product-Parity Runtime/Evidence Compression

## Scope And Baseline

The bounded surface is 1,042 effective Python lines across:

- `tests/unit/product/parity/snapshots.py` (154)
- `tests/unit/product/parity/test_runners.py` (333)
- `tests/unit/product/parity/test_evidence_writing.py` (345)
- `tests/unit/product/parity/test_report.py` (210)

The measure is the repository's canonical `ethos_core.measure.effective_code_lines`
contract at base `78efdedb7b0a54177099ef80ca09108ed32851db`; comments, blanks,
docstrings, and padding strings are excluded. The lane changes tests and the
existing test-only `snapshots.py` helper only.
Production parity code is deliberately excluded.

## Decision

Use a compact test-fixture algebra for inert repository setup, Work-Lane lease
binding, literal shadow report construction, evidence-file placement, and exact
public assertion fragments. Use `pytest.mark.parametrize` only for a finite
partition whose operation and observable contract are identical. Each retained
case gets a domain-named `id`.

The fixtures may construct literal dictionaries and files, but may not evaluate
parity semantics, derive expected gaps, normalize a product result, or encode
runtime routing. Those responsibilities remain in the production modules.

## Retained Boundaries

Keep independently named tests for:

1. protected-root write refusal;
2. default planned shadow behavior;
3. missing embedded backend;
4. timeout/process-malformation/exit-code classification;
5. rooted versus current-working-directory external invocation;
6. profile-specific evidence destination;
7. stale product/target evidence freshness.

## Cutover And Evidence

1. Create baseline OpenSpec and record the three-file ELOC total.
2. Replace only visibly repeated setup and exact assertions with fixture/table
   forms, deleting the former bodies.
3. Run focused parity tests with coverage, format/lint, and source-budget delta.
4. Regenerate generic parity evidence from the admitted Work Lane, commit all
   tracked outputs, then run HEAD-bound full proof.
5. Archive the carrier before candidate land; close out and retire only after
   accepted-root promotion.

## Success Criteria

- The scoped corpus is a net deletion from the 1,042-effective-line baseline.
- Named diagnostic boundaries and public JSON contracts remain covered.
- No production parity behavior changes.
- The repository's 100-percent coverage and full proof remain green.
