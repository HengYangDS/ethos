## 1. Official Contract

- [x] 1.1 Strictly validate this Change and inspect the repository-locked
  OpenSpec JSON projection for a real completed `skip_specs: true` fixture
- [x] 1.2 Add a RED regression proving that the official spec-free projection
  compiles deterministic non-empty acceptance while undeclared or incomplete
  zero-delta projections fail closed

## 2. Compiler

- [x] 2.1 Implement the minimum change in the existing OpenSpec Commitment
  compiler; add no carrier, schema, registry, or compatibility path
- [x] 2.2 Run focused compiler and archive/currentness tests and verify the
  retired `deltas=[]` rejection contract has no stale callers

## 3. Closeout

- [x] 3.1 Run strict OpenSpec validation, Ruff, type/import/module-layout checks,
  and the affected lifecycle test set
- [x] 3.2 Verify the existing public archive, accepted closeout, immutable-runtime,
  and lane-retirement transition contracts remain green
