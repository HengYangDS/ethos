## 1. Preserve the hosted failures

- [x] 1.1 Add a Windows-layout regression proving immutable runtime discovery
  reads the installed wheel metadata and retains the unique `ethos` console
  entrypoint; verify the focused test fails with
  `hook_runtime_entrypoint_missing` before the repair.
- [x] 1.2 Add an identity-drop regression proving the shared Git boundary keeps
  the runner's exact `safe.directory` and explicit author/committer identity
  while preserving repository-local identity policy and hiding ambient Git
  configuration; verify the focused test fails before the repair.

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
- [x] 3.2 Produce exact-HEAD full proof for the complete source change and
  confirm that every repository gate passes before the official archive
  transition.
