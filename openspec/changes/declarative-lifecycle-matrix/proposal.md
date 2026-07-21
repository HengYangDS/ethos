## Why

Lease operations still mixed procedural CLI assembly with parallel retirement
effects, incomplete compare-and-swap envelopes, and a Work Lane start sequence
that could confuse pre-existing carrier state with state created by the current
attempt. That combination obscured the declared lifecycle matrix and could
either delete unrelated state or revoke coordination before carrier cleanup was
complete.

## What Changes

- Compile renew, resume, handoff-offer, and handoff-accept generation
  transitions from the tracked workflow declaration through one pure lease
  reducer.
- **BREAKING** Replace parallel landed and superseded Python APIs with one strict
  Pydantic request and one linked-retirement effect.
- Bind every lease mutation to the exact lease ID, holder, epoch, lane ref,
  expected head, row expiry, and raw payload digest under a SQLite generation
  lock.
- Recheck the accepted control root and accepted ref at effect time, remove the
  clean linked worktree, and compare-and-delete the exact lane ref in one Git ref
  transaction.
- Roll back the lease deletion on failure and restore the lane ref
  create-if-absent when the SQLite commit fails after Git removal.
- Remove thin wrappers, re-exports, obsolete compatibility summary code, and
  redundant coverage aggregation.
- Remove the archived Claim-specific source-budget rebase resolver and its
  hard-coded dated carrier/path matrix; the generic semantic ledger resolver is
  the sole non-parity conflict path.
- Remove every ignored-state lease migration and the lease subsystem's false
  ownership of a shared database-wide version; only a fresh or structurally
  exact current lease table remains supported.
- Enforce one current lease per Work Lane subject in SQLite rather than through
  parallel Python preflight and ambiguity branches.
- Use the same exact revoke effect for ordinary and accepted-policy-bound
  unavailable-holder retirement; unavailable-holder recovery is a policy mode,
  not a second effect owner.
- Make Work Lane start no-clobber: reject a pre-existing target path or ref
  before acquiring a lease, recheck after acquisition, and revoke the new lease
  only after every carrier created by the failed attempt is proven absent.
- Compress the 17 overlong canonical OpenSpec requirement texts without
  removing scenarios or obligations; official strict validation must report
  zero issues at every level.
- Set Taplo's native success log floor to warning so configuration gates are
  quiet on success while preserving real warning/error output and exit status.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=declarative-lifecycle-matrix;
  reuse=extend; change=modify; facet:lifecycle=runtime,validation;
  facet:surface=cli,evidence; facet:authority=source,test,openspec,claim,evidence

## Impact

Affected surfaces are the lease and handoff contracts, linked and exceptional
retirement adapters, Work Lane start saga, Cyclopts lane commands, exact
lease/ref race regressions, invalid-state classification, quality ratchets, the
current Claim/Chronicle, canonical quality and repository-governance specs, and this OpenSpec carrier.

## Out Of Scope

General intent continuity, takeover after session destruction, bounded parallel
execution, dirty-content recovery, foreign-lane authority, remote publication,
hosted CI, and the later compatibility-surface-zero wave.
