## Why

An unrelated out-of-process verifier can issue a read-only ownerless closeout
admission for one exact clean lane, but an admission verdict does not authorize
a later destructive effect by itself. ETHOS currently has no target-scoped
effect fence, does not validate every retired external-verifier response
binding, can omit the
accepted ref from the deletion CAS, and can leave a destructive or uncertain
partial transition without a convergent receipt-and-cleanup path.

## What Changes

- Add a bounded retired external-verifier adapter that validates every
  security-bearing response field against the exact decision bytes, observation, executor, accepted
  branch, and accepted head supplied by ETHOS.
- Add a Git-common-directory target fence acquired through SQLite CAS after
  retired external-verifier admission and before effect; lease acquisition for the same lane fails while
  the fence exists.
- Add one clean-ownerless retirement primitive that prepares an atomic accepted
  ref verification plus exact target-ref deletion, removes the registered
  worktree without force, commits the ref transaction, and verifies
  three-state ref, worktree, path, coordination, decision, and fence outcomes
  before a receipt is issued.
- Bind completion receipts to executor, retired external-verifier decision
  digest, accepted head, coordination binding, target binding, and postcondition digest.
- Make inflight and partial ownerless target reservations visible to inventory;
  permit only exact same-decision retry, exact completed-effect receipt
  recovery, and exact receipt-present cleanup convergence.
- Isolate armed-hook proof repositories from the caller's writable editable
  environment so an E2E cannot rewrite the outer test runtime.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=ownerless-closeout-effect-fence;
  reuse=extend; change=modify; facet:lifecycle=retirement,recovery;
  facet:surface=adapter,state,receipt,inventory,test,openspec,contract,schema,docs;
  facet:authority=source,test,contract,evidence,external-verifier-admission

## Out Of Scope

- Any real retirement of work/ownerless-lane-first-closeout or another existing
  foreign lane.
- Dirty preserve-retire, valid-owner retirement, raw Git deletion, raw SQLite
  deletion, remote publication, hosted CI mutation, GitLab availability, or a
  claim that the local fence is a distributed or filesystem lock.
