## 1. Archive authority continuity

- [x] 1.1 Add focused regressions proving that an authorized refresh preserves
  the exact archived Change and never substitutes a nearer unrelated archive.
- [x] 1.2 Resolve the rewritten archive tip from the existing archive and
  refresh Attestation chain, and verify the focused archive-transition tests.

## 2. Convergence

- [x] 2.1 Verify strict OpenSpec validation, formatting, linting, typing, and the
  archive-transition regression suite.
- [x] 2.2 Verify real post-refresh archive resolution recovers the exact
  archived Change and current rewritten head without
  `proof_archive_scope_stale`.
