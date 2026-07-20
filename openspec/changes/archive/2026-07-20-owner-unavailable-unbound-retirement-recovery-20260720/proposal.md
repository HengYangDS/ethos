# Owner-unavailable unbound retirement recovery

## Why

An accepted-ancestor unbound Work Lane can retain an active lease after its
source worktree and holder disappear. The normal ETHOS handoff requires a source
holder offer, while ordinary exceptional retirement correctly refuses a foreign
lease. Without a constrained recovery transition, this residue cannot converge
without bypassing native lease/ref controls.

## What Changes

- Add one explicit `--owner-unavailable-recovery` mode to the existing native
  `ethos lane retire unbound` command.
- Require the accepted target Chronicle to bind the exact active source lease
  ID, holder, epoch, expected head, source worktree path, and verified absence
  of that path.
- Require a non-empty recovery actor different from the source holder, and
  preserve the existing expected-head, Claim, accepted-Chronicle,
  break-glass, irreversible-confirmation, re-observation, native CAS, guarded
  ref deletion, and receipt controls.
- Reject generic foreign takeover, a source path that exists, and any stale or
  malformed source lease binding.

## Capabilities

- `repository-governance`: subject=owner-unavailable-unbound-retirement-recovery;
  reuse=extend; change=modify;
  facet:lifecycle=exceptional-unbound-retirement,accepted-policy-admission,
  native-lease-cas,receipt-bound-closeout;
  facet:surface=cli,mutation,lease,claim,evidence,openspec,test;
  facet:authority=accepted-chronicle,active-claim,exact-lease-generation,
  fresh-observation,native-cas,receipt.

## Out Of Scope

- Manual Git ref or SQLite lease deletion, source-holder impersonation, normal
  handoff replacement, force worktree removal, batch cleanup, remote mutation,
  hosted CI, or vendor/session-specific authority.
