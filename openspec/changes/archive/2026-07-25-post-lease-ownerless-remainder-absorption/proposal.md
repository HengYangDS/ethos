## Why

Four Work Lanes that were protected by valid leases during the prior closeout
now have no lease or Claim. Three are clean diverged historical carriers. One is
a dirty, staged-plus-unstaged ownerless closeout compression attempt. Raw
cleanup would either retain obsolete lanes indefinitely or lose unique dirty
bytes; blanket preservation would also evade semantic judgment.

## What Changes

- Bind the exact four branches, heads, merge bases, worktree registrations,
  status and patch digests, ownerless state, and empty occupancy observations.
- Distill useful invariants into one current Chronicle while rejecting replay of
  incomplete, stale, or valid-owner-overlapping implementations.
- Authorize three later native clean retire decisions and one later native
  preserve-retire decision only after this carrier is archived, proved, landed,
  and accepted-closed.
- Keep exact package clear separate and manifest-bound.
- Leave every valid-owner lane observe-only.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=post-lease-ownerless-remainder-absorption;
  reuse=extend; change=modify; facet:lifecycle=validation,retirement,recovery;
  facet:surface=openspec,claim,chronicle,evidence;
  facet:authority=git,evidence,test,native-command.

## Out Of Scope

Taking over or editing any valid-owner lane, replaying provisional migration or
compression code, weakening exact ownerless admission, raw Git deletion,
clearing a package before a separate accepted exact-manifest decision, remote
publication, or hosted-CI claims.
