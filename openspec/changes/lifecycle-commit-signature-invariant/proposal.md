# Change: Enforce lifecycle commit signature policy

## Why

ETHOS creates commit objects for lane materialization and Commitment rebinds.
Those plumbing commits bypassed Git's effective `commit.gpgsign` policy, so an
otherwise proven accepted suffix could contain unsigned lifecycle commits and
fail only at publication provenance admission. Existing single-commit identity
repair also cannot repair an older unsigned commit because every descendant OID
changes when that commit is re-signed.

## What Changes

- Make the sole commit-object owner inherit the repository's effective signing
  policy and verify signed objects before any ref mutation.
- Keep unsigned lifecycle commits valid only when signing is explicitly not
  enabled for the repository.
- Extend the existing `lane repair-identity` capability with a receipt-bound,
  exact-CAS suffix mode that re-signs one linear suffix, preserves each commit's
  tree/message/author/committer metadata, and advances only the observed work,
  candidate, accepted, and configured release refs.
- Preserve the existing one-commit mode and authority model; do not add another
  command, state store, signature policy, or general history-rewrite authority.

## Impact

- Affected capability: command-plane lifecycle mutation and recovery.
- Affected code: commit-object creation, identity repair, its CLI projection,
  and focused lifecycle regressions.
- Out of scope: runtime relocation, adopter profile migration, Forge
  publication, proof-generation selection, and AIGW/Proxy mutation.
