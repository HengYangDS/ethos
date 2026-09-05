## 1. Stable Release Inventory

- [x] 1.1 Verify every repository-controlled direct Python, Node, downloaded-tool, runtime, hosted-action, and container-image owner against its authoritative upstream and retain a machine-readable audit receipt.
- [x] 1.2 Confirm already-current identities remain unchanged and verify the resulting diff contains no version-only churn without a newer stable release.

  Evidence: the 2026-09-05 upstream audit covered 30 Python inputs, five Node
  packages, two Node runtime lines, four downloaded tools, five hosted actions,
  and two OCI images with no stale result; receipt SHA-256
  `95d76a3fec81dfdac79e7471a3347c68998ef4b90f3b44a5e147b33368351def`.

## 2. Authority and Lock Convergence

- [x] 2.1 Make the exact target source checkout root `.venv` own locked uv, build-backend, and dependency-byte supply; prove an older invoking runtime is not required to contain the newer source build closure.
- [x] 2.2 Advance stale Python dependency owners and regenerate the complete `uv.lock` closure with uv; verify `uv lock --check` passes.
- [x] 2.3 Advance the exact official OpenSpec owner and regenerate `package-lock.json` with npm; verify the installed CLI reports the selected version.
- [x] 2.4 Advance uv CI and emulator image owners to immutable verified digests, materialize provider projections from their existing templates, and verify projection consistency.
- [x] 2.5 Advance `VERSION` and its npm projection to `0.2.0-alpha.4`, update exact version assertions and current normative documentation, and verify no stale current-owner literal remains outside historical carriers or deliberate compatibility fixtures.

  Evidence: the root environment reports uv `0.12.10` and OpenSpec `1.12.0`;
  `uv lock --check`, npm lock installation, CI projection equality, and the
  focused runtime/version/release suite all pass. The package-only lifecycle
  proved that an older invoking runtime can activate the new source from the
  target checkout's lock-current `.venv`.

## 3. Compatibility Proof

- [x] 3.1 Run official strict OpenSpec validation plus focused supply-chain, dependency, CI-template, version, and release-asset tests.
- [x] 3.2 Run format, lint, type, schema, documentation, and repository-hygiene gates and resolve all warnings and errors.
- [x] 3.3 Run the complete local repository test graph on the frozen overlay and
  verify the coverage floor and every required static gate pass without
  warnings.
- [x] 3.4 Build Python and npm artifacts, run package-only installation and CLI identity checks, generate the SBOM, and verify immutable artifact digests.

  Evidence: strict OpenSpec validation passed; 146 focused tests and the wider
  361-test runtime/supply suite passed; 16 static, structure, documentation,
  and repository gates passed; the full test graph passed with 2,069 tests,
  one skip, and 93.31% coverage. Pre-commit artifact acceptance produced an
  offline-installable wheel, package-only runtime identity, complete lifecycle
  receipt, npm package manifest, and Syft SPDX 2.3 SBOM. Final artifacts must be
  rebuilt after the signed commit so their source identity binds exact HEAD.

## 4. Freeze Boundary

- [x] 4.1 Mark only evidenced tasks complete and validate the Change strictly,
  freezing one coherent implementation boundary for a signed conventional
  commit and exact-HEAD proof.

## Lifecycle Transition Boundary

After every task above is complete, the implementation requires one signed
commit and exact-HEAD full proof before official archive. Archive creates a
distinct signed HEAD that then requires reproof, candidate and accepted exact
CAS, final Python and npm artifact reconstruction, fresh immutable package-only
runtime activation and readback, exact publication of the same accepted object
to every declared remote, hosted-plane observation, and retirement of this Work
Lane with no ref, worktree, Lease, temporary environment, or unconsumed artifact
residue. These are mandatory terminal transitions after the checklist, not
self-referential pre-commit tasks, and MUST NOT be claimed before their exact
observations exist.
