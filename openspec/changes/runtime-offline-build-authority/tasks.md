## 1. Source bootstrap authority

- [x] 1.1 Add a regression proving source hook installation succeeds with an
  empty uv cache when the active environment matches the lock; verify the
  installed runtime executes its public version command.
- [x] 1.2 Require a locked offline active-environment check before source wheel
  output, and verify drift fails before materialization.

## 2. Minimal immutable runtime

- [x] 2.1 Build with the verified active environment, then copy and hash-prune it
  to the production closure before installing the exact content-addressed ETHOS
  wheel; verify focused runtime installation tests.
- [x] 2.2 Verify package-only relocation, runtime manifest identity, and removal
  of development-only dependencies from the immutable production closure.

## 3. Lifecycle closure

- [x] 3.1 Run format, static checks, strict OpenSpec validation, and focused
  runtime installation tests.
- [x] 3.2 Verify selector activation, complete hook projection, idempotence,
  failure atomicity, and consumer-aware obsolete-generation collection.
