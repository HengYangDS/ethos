## 1. Preserve the hosted failures

- [x] 1.1 Add a Windows-layout regression proving immutable runtime discovery
  reads the installed wheel metadata and retains the unique `ethos` console
  entrypoint; verify the focused test fails with
  `hook_runtime_entrypoint_missing` before the repair.
- [x] 1.2 Add an identity-drop regression proving the shared Git boundary keeps
  the runner's exact `safe.directory` and deterministic identity overlay while
  hiding ambient Git configuration; verify the focused test fails with dubious
  ownership before the repair.

## 2. Repair the unique owners

- [x] 2.1 Correct immutable Python image metadata/entrypoint discovery in the
  existing materialization owner and verify package-only runtime tests pass on
  POSIX plus the Windows-layout regression.
- [x] 2.2 Correct explicit indexed Git configuration propagation in the shared
  Git subprocess owner, remove redundant fixture-level handling if any, and
  verify source identity plus commit fixtures pass under the reduced identity.

## 3. Prove and close the change

- [x] 3.1 Prove repository-wide reference closure, Ruff, focused runtime/Git
  tests, affected architecture tests, and strict OpenSpec validation.
- [ ] 3.2 Produce exact-HEAD full proof, archive and reproof the official Change,
  advance candidate by exact CAS, update the existing proposal ref, and verify
  GitHub Windows plus GitLab identity-drop hosted jobs pass.
- [ ] 3.3 Advance accepted by exact CAS, activate a newly versioned immutable
  package-only runtime, verify source/tree/package/runtime readback, publish
  `dev` before `main` to both remotes, and retire the proposal and owner lane.
