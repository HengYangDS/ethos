# Tasks

- [x] **1.** Lock the exact `@fission-ai/openspec@1.9.0` package and regenerate
  the npm lockfile from the official registry with its integrity verified.
- [x] **2.** Align the current governance documentation and archive-transition
  contract with OpenSpec 1.9.0 while leaving historical archives unchanged.
- [x] **3.** Prove the locked package through `npm ci`, OpenSpec strict
  validation/doctor, and the focused archive-transition contract test.

| Outcome | Task | Evidence |
| --- | ---: | --- |
| `distribution:OpenSpec package and lockfile have one exact authority` | 1 | `npm-ci:openspec-1.9.0` |
| `repository-governance:Current contract names OpenSpec 1.9.0` | 2 | `tests:archive-transition-contract` |
| `quality:OpenSpec 1.9.0 validation and doctor pass` | 3 | `openspec:strict-doctor` |
