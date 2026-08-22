## 1. Contract And RED

- [x] 1.1 Add strict capability deltas for global semantic closure, exact
  category vocabulary, current-carrier selection, and the observational trust
  boundary; verify with `openspec validate repository-semantic-closure --strict`.
- [x] 1.2 Add a real duplicate-owner regression proving the current set-based
  audit falsely passes; verify the test fails for the missing closure behavior.
- [x] 1.3 Add orphan and unknown relation regressions proving partial green
  checks cannot produce aggregate `pass`; verify each failure names provenance.

## 2. Unique Owner Replacement

- [x] 2.1 Preserve owner, producer, consumer, and selector provenance while
  parsing each existing native carrier once; verify deterministic fact tests.
- [x] 2.2 Compile one typed closure with missing, duplicate, orphan,
  superseded, conflict, and unknown categories; verify category matrix tests.
- [x] 2.3 Integrate closure into `repository_audit()` and remove the parallel
  set-only `reference_ownership` and unevaluated semantic-equivalence reports;
  verify aggregate producer-to-consumer tests.
- [x] 2.4 Repair every current-tree closure gap without literal exception lists;
  verify accepted repository audit reports zero in every category.
- [x] 2.5 Prove repository-wide reference closure and delete superseded helpers,
  report shapes, tests, and documentation; verify searches and architecture
  tests find no incumbent surface.

## 3. Validation And Closeout

- [x] 3.1 Run strict OpenSpec validation plus focused format, Ruff, type,
  architecture, repository-policy, and audit tests.
- [ ] 3.2 Run the complete applicable proof and verify current HEAD/tree and
  semantic-closure evidence.
- [ ] 3.3 Archive through the public lifecycle, rerun post-archive proof, land
  exact CAS, project the accepted runtime, and retire this lane.
