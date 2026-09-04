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

## 3. Prove pre-archive closure

- [x] 3.1 Resolve every full-proof failure, then verify focused behavior,
  format ownership, source budget, unit architecture, coverage floor, strict
  OpenSpec validity, and repository-wide reference closure.

## Lifecycle Transition Boundary

After every task above is complete, create a signed closure commit and run
exact-HEAD full proof before official archive. Archive creates a distinct signed
HEAD that then requires reproof, candidate and accepted exact Git CAS, fresh
immutable package-only runtime materialization and readback, exact publication
of the same accepted object to every declared peer, independent native Linux,
macOS, and Windows observation, and retirement of this lane plus the previously
absorbed `github-workflow-syntax-proof-closure` lane. These are mandatory
terminal transitions after the checklist, not self-referential pre-archive
tasks, and MUST NOT be claimed before their exact observations exist.
