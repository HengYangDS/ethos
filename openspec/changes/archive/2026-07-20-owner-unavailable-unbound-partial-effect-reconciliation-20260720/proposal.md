## Why

One historical owner-unavailable exceptional-retirement attempt can leave a
strictly narrower residue: the source `work/*` ref has already disappeared,
but its exact active foreign lease remains. Re-running ordinary retirement is
incorrect because it requires a present accepted-ancestor ref; raw lease or ref
mutation would hide the partial effect and bypass the native evidence boundary.

## What Changes

- Add a separate native `ethos lane retire reconcile-ref-absent` command for
  one accepted-policy-bound, ref-absent owner-unavailable residue.
- Require a current accepted Chronicle to bind the exact remaining lease tuple
  and an immutable prior native retirement-attempt record; require a different
  non-empty recovery actor, source-path absence, explicit authorization,
  break-glass, and irreversible confirmation.
- Write no-clobber reconciliation attempt and receipt records around the exact
  native lease-generation CAS; preserve the absent ref and require postconditions
  for ref, worktree, lease, protected refs, and Chronicle bytes.
- Make the ordinary exceptional compare-and-delete protected-ref transaction
  hook-compatible through same-value protected-ref CAS updates.

## Capabilities

- `repository-governance`: subject=owner-unavailable-unbound-partial-effect-
  reconciliation; reuse=extend; change=modify;
  facet:lifecycle=exceptional-unbound-retirement,partial-effect-reconciliation,
  native-lease-cas,receipt-bound-closeout;
  facet:surface=mutation,lease,claim,evidence,openspec,test;
  facet:authority=accepted-chronicle,active-claim,immutable-attempt,
  exact-lease-generation,fresh-observation,native-cas,receipt.
- `command-plane`: subject=owner-unavailable-unbound-partial-effect-
  reconciliation; reuse=extend; change=modify;
  facet:lifecycle=exceptional-unbound-retirement,partial-effect-reconciliation;
  facet:surface=cli,docs,command-registry;
  facet:authority=explicit-controls,accepted-policy,exact-target,
  vendor-neutral-identity.

## Impact

- Affects the exceptional unbound-retirement mutation adapter, observation,
  policy, records, reporting, public CLI, command registry, documentation, and
  focused lifecycle regression tests.
- Does not add remote mutation, force worktree removal, generic lease takeover,
  raw Git/SQLite cleanup, or vendor-specific authority.

## Out Of Scope

- Recreating or deleting a source ref, source-holder impersonation, ordinary
  handoff replacement, force worktree removal, batch cleanup, remote mutation,
  hosted CI claims, or vendor/session-specific authority.
