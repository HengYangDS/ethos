## 1. Specify The Retirement Boundary

- [x] 1.1 Validate the official OpenSpec Change with `openspec validate lane-residue-terminal-closure --strict` and resolve any schema or artifact gap before production edits
- [x] 1.2 Add focused regressions proving linked landed retirement is Commitment-free and admits only the specified valid, expired, or missing Lease states while retaining unsafe-state blocks

## 2. Implement The Existing Public Transition

- [x] 2.1 Remove proof and Commitment reconstruction from the linked retirement plan and verify its focused unit tests pass with `commitment is None`
- [x] 2.2 Make landed retirement admission and the SQLite transaction distinguish valid, expired, missing, and unknown Lease observations, and verify exact holder, actor, generation, and absence checks
- [x] 2.3 Preserve exact Git CAS, accepted-ref assertions, worktree compensation, Lease rollback, and terminal postcondition evidence, and verify the linked retirement apply matrix

## 3. Prove And Close The Change

- [x] 3.1 Run focused retirement tests, affected static checks, and the repository proof ladder with no warnings or cleanup residue
- [x] 3.2 Freeze the final diff, close active canonical-reference contradictions,
  and verify non-interactive signing and public archive readiness without
  claiming evidence that can exist only after the implementation commit.

## Lifecycle Transition Boundary

After every task above is complete, the implementation requires a signed commit
and exact-HEAD proof before official archive. Archive creates a distinct signed
HEAD that then requires reproof, candidate and accepted exact CAS, fresh
immutable-runtime activation and readback, and retirement of this Work Lane
through the newly accepted public `lane retire landed` transition. These are
mandatory terminal route transitions, not self-referential pre-commit tasks, and
MUST NOT be claimed before their own exact observations prove them.
