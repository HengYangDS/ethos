## 1. Authority And Scope

- [x] 1.1 Restore the prior archived Commitment through public exact-CAS rebind and verify the Lease advances without changing the three-file overlay.
- [x] 1.2 Start this successor Change with both relevant predecessor digests and verify `ethos status --json` attributes only its current generation as authorized.

## 2. Runtime Cache

- [x] 2.1 Derive one cache root shared by pytest-xdist workers and verify distinct worker base paths converge to it.
- [x] 2.2 Publish the source-bound runtime template under a cross-process lock and verify duplicate installers perform one expensive build.
- [x] 2.3 Release the global runtime lock before repository-local cloning and verify independent repositories receive distinct valid runtime paths.
- [x] 2.4 Validate templates before reuse and verify an invalid candidate is not selected.
- [x] 2.5 Prove repository-local Python, entrypoint, manifest, and venv metadata remain isolated while a standard `.pth` projection shares only the controller-owned read-only `site-packages`; keep test subprocess bytecode writes disabled.
- [x] 2.6 Publish and validate the template in the pytest controller before xdist workers start; prove workers can install from it when their fallback builder is unavailable.

## 3. Verification And Closeout

- [x] 3.1 Run the focused cache tests and the seven-node pytest-xdist reproducer; verify all tests pass without worker timeout.
- [x] 3.2 Run format before lint, source-budget, unit-architecture, and coverage-floor gates; verify each required gate passes.
- [ ] 3.3 Prove strict OpenSpec validity and archive readiness, then use the official OpenSpec-backed ETHOS transition to archive the Change before the final HEAD-bound proof and public closeout.
