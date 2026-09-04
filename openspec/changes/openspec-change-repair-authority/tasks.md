## 1. Regression Contract

- [x] 1.1 Add focused current-resolution tests proving that structured `ERROR`
  and `WARNING` issues for the selected active Change admit only their uniquely
  matching existing official artifact, and observe the assertions fail before
  production code changes.
- [x] 1.2 Add negative coverage for mismatched Change ids, `INFO` issues,
  malformed or traversing paths, absent outputs, ambiguous base resolution,
  symlinked outputs, unrelated requested paths, and mixed requests; verify
  every case remains blocked.
- [x] 1.3 Preserve focused canonical-spec repair coverage and verify the active
  Change path does not require a valid Commitment while canonical repair still
  does.

## 2. Singular Validation Repair Owner

- [x] 2.1 Replace the canonical-only repair helper with one official validation
  repair owner that derives both canonical and active-Change exact paths from
  the current governance report; verify the focused scope tests pass.
- [x] 2.2 Resolve active-Change issue paths only by unique intersection with
  current official artifact outputs under the selected Change root and its
  `specs/` root; retain lexical artifact identity, require exact regular files,
  and verify no symlink, directory, absent path, or second Change is admitted.
- [x] 2.3 Update the current resolver to consume the renamed owner, remove all
  superseded symbol references, and verify admission and OpenSpec lifecycle
  tests pass.

## 3. Original Deadlock And Repository Proof

- [x] 3.1 Evaluate the originally blocked prewrite against
  `openspec-spec-free-prewrite-authority`: its material-scope decision admits
  only `specs/repository-governance/spec.md`, while an adjacent artifact and a
  mixed request remain uncovered. The cross-worktree command remains
  fail-closed on source-bound runtime identity until this Change reaches an
  immutable accepted runtime.
- [x] 3.2 Complete repository reference closure, format, lint, types, and the
  smallest affected gate set with no warnings or stale owner names.
- [x] 3.3 Validate the official Change strictly and freeze the implementation
  boundary for one signed conventional commit. Evidence: the affected public
  suite passed 180 tests; targeted Ruff, Ruff format, and ty passed; module
  layout and product-boundary gates passed; and the superseded owner name has
  no current source, test, rule, documentation, or active OpenSpec reference.

## Lifecycle Transition Boundary

After every task above is complete, the implementation requires one signed
commit and exact-HEAD full proof before official archive. Archive creates a
distinct signed HEAD that then requires reproof, candidate and accepted exact
CAS, fresh immutable package-only runtime materialization and readback, the
original spec-free prewrite recheck under that runtime, and retirement of this
Work Lane with no ref, worktree, or Lease residue. These are mandatory terminal
transitions after the checklist, not self-referential pre-commit tasks, and
MUST NOT be claimed before their exact observations exist.
