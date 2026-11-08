# Tasks

## 1. Exact index admission

- [x] 1.1 Add mixed-content and stale-prestate regressions; observe focused RED
  against the current public admission and preserve native failure evidence.
  Evidence: `build/runtime/work/index-prewrite/red.xml` and sibling RED reports.
- [x] 1.2 Implement the explicit index target with disposable preparation and
  shared staged admission; pass focused tests with real index/worktree preserved.
  Evidence: `build/runtime/work/index-prewrite/object-custody-green.xml`.
- [x] 1.3 Document the target and its effect boundary in the command reference;
  pass public CLI, default-target and sibling admission regressions.
  Evidence: `build/runtime/work/index-prewrite/owner-closure-final.xml` (440 passed)
  and `test-owner-final.xml` (37 passed after splitting native journeys).

## 2. Consumer qualification

- [x] 2.1 Replay the exact Alphasim and di-effect patches through candidate
  admission without real index mutation; verify source and staging preservation.
  Evidence: `build/runtime/work/index-prewrite/*-owner-closure-replay.json`;
  both are blocked diagnostics, not installed-runtime acceptance.
- [x] 2.2 Run module layout, format, strict OpenSpec and relevant quality gates;
  verify owned temporary residue is absent and retain failed evidence.
  Evidence: `build/runtime/work/index-prewrite/test-owner-final-gates.json`,
  `owner-closure-source-gates.json`, strict validation and replay reports.

## Workflow follow-up

- Commit the source with native signing and prove the exact committed HEAD.
- Publish and land through the normal reviewed ETHOS delivery route.
- Qualify the released runtime at each adopter before switching its bindings.
- Archive through the governed continuation after the Change obligations close.
