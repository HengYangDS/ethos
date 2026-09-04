## 1. Establish the host-portability failures

- [x] 1.1 Add a RED regression proving a repository-owned Git content policy
  makes a clean checkout's effective source tree equal `HEAD^{tree}` even when
  ambient `core.autocrlf=true` is hidden during identity observation.
- [x] 1.2 Add a RED regression proving an installed wheel referenced by a
  Windows drive-letter `file:` URL resolves through native path semantics, while
  non-local or non-wheel provenance remains rejected.

## 2. Restore one package identity across hosts

- [x] 2.1 Add the minimal root Git attribute policy, inspect renormalization for
  unintended tracked-byte changes, and verify real dirty overlays still produce
  a distinct effective tree.
- [x] 2.2 Replace manual URL path extraction with the standard-library native
  file-URL conversion at the existing wheel resolver and verify the focused
  runtime-input tests pass on the declared Python floor.
- [x] 2.3 Run focused source-identity, build-identity, runtime-materialization,
  package-acceptance, and host-portability tests plus strict OpenSpec validation
  and repository-wide reference closure.

## 3. Prove and close the bounded change

- [ ] 3.1 Commit the implementation with an admitted signed subject and run the
  exact-HEAD full local proof once at the frozen boundary.
- [ ] 3.2 Archive the official Change, re-prove the archive commit, complete
  candidate and accepted exact Git CAS, and install and read back a fresh
  immutable package-only runtime.
- [ ] 3.3 Publish the exact accepted commit to every declared peer and verify
  native Linux, macOS, and Windows package-conformance observations report the
  same source commit/tree with no wheel-provenance failure.
- [ ] 3.4 Retire this lane and the previously absorbed
  `github-workflow-syntax-proof-closure` lane only after their required hosted
  observations are terminal and all owned refs, worktrees, Leases, and temporary
  resources are absent.
